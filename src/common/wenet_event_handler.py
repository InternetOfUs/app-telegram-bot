import abc
import logging
from typing import Optional, List
from threading import Lock

import requests

from chatbot_core.model.context import ConversationContext
from chatbot_core.model.details import TelegramDetails
from chatbot_core.model.event import IncomingSocialEvent, IncomingCustomEvent
from chatbot_core.model.user_context import UserConversationContext
from chatbot_core.nlp.handler import NLPHandler
from chatbot_core.translator.translator import Translator
from chatbot_core.v3.connector.social_connector import SocialConnector
from chatbot_core.v3.connector.social_connectors.telegram_connector import TelegramSocialConnector
from chatbot_core.v3.handler.event_handler import EventHandler
from chatbot_core.v3.handler.helpers.intent_manager import IntentManagerV3, IntentFulfillerV3
from chatbot_core.v3.logger.event_logger import LoggerConnector
from chatbot_core.v3.model.actions import UrlButton
from chatbot_core.v3.model.messages import RapidAnswerResponse, TextualResponse, TelegramTextualResponse
from chatbot_core.v3.model.outgoing_event import OutgoingEvent, NotificationEvent
from common.cache import BotCache
from common.messages_to_log import LogMessageHandler
from uhopper.utils.alert.module import AlertModule
from wenet.interface.client import Oauth2Client
from wenet.interface.exceptions import NotFound, RefreshTokenExpiredError
from common.authentication_event import CreationError
from wenet.interface.service_api import ServiceApiInterface
from common.authentication_event import WeNetAuthenticationEvent
from common.callback_messages import TextualMessage
from wenet.model.callback_message.message import Message
from wenet.storage.cache import RedisCache
from common.callback_messages import MessageBuilder

logger = logging.getLogger("uhopper.chatbot.wenet")


class WenetEventHandler(EventHandler, abc.ABC):
    """
    Generic event handler for Wenet chatbots, taking care of authentication and basic interfacing with Wenet and
    Telegram APIs.

    Methods to be implemented by any class that extends this one:
    - action_info(incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent
    - action_error(incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent
    - cancel_action(incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent
    - handle_wenet_textual_message(message: TextualMessage) -> NotificationEvent
    - handle_wenet_notification_message(message: TaskNotification) -> NotificationEvent
    - handle_wenet_authentication_result(message: WeNetAuthentication) -> NotificationEvent

    Attributes:
        - instance_namespace, bot_id, handler_id, alert_module, connector, nlp_handler, translator,
        delay_between_messages_sec, delay_between_text_sec, logger_connectors as the normal EventHandler
        - telegram_id: telegram secret code to communicate with Telegram APIs
        - wenet_instance_url: the url of the Wenet instance
        - wenet_hub_url: the url of the Wenet hub frontend, where users are redirected for authentication
        - app_id: the Wenet app Id with which the bot works
        - client_secret: the secret key to use Wenet API
        - redirect_url: the url used for user redirection after authentication
        - wenet_authentication_url
        - wenet_authentication_management_url
        - task_type_id: the type of the task used by the bot
    """
    TELEGRAM_GET_ME_API = 'https://api.telegram.org/bot{}/getMe'

    PREVIOUS_INTENT = "previous_message_intent"

    # context keys
    CONTEXT_CURRENT_STATE = "current_state"
    CONTEXT_WENET_USER_ID = 'wenet_user_id'
    CONTEXT_TELEGRAM_USER_ID = "telegram_user_id"
    # all the recognize intents
    INTENT_START = '/start'
    INTENT_CANCEL = '/cancel'
    INTENT_HELP = '/help'
    INTENT_INFO = '/info'
    INTENT_BUTTON_WITH_PAYLOAD = "bwp--{}"

    def __init__(self,
                 instance_namespace: str,
                 bot_id: str,
                 handler_id: str,
                 telegram_id: str,
                 wenet_instance_url: str,
                 wenet_hub_url: str,
                 app_id: str,
                 client_secret: str,
                 redirect_url: str,
                 wenet_authentication_url: str,
                 wenet_authentication_management_url: str,
                 task_type_id: str,
                 community_id: str,
                 alert_module: AlertModule,
                 connector: SocialConnector,
                 nlp_handler: Optional[NLPHandler],
                 translator: Optional[Translator],
                 delay_between_messages_sec: Optional[int] = None,
                 delay_between_text_sec: Optional[float] = None,
                 logger_connectors: Optional[List[LoggerConnector]] = None):
        super().__init__(instance_namespace, bot_id, handler_id, alert_module, connector, nlp_handler, translator,
                         delay_between_messages_sec, delay_between_text_sec, logger_connectors)

        self.cache = BotCache.build_from_env()
        self.oauth_cache = RedisCache.build_from_env()

        self.telegram_id = telegram_id
        # getting information about the bot
        info = requests.get(self.TELEGRAM_GET_ME_API.format(self.telegram_id)).json()
        if not info["ok"]:
            logger.error("Not able to get bot's info, Telegram APIs returned: %s" % info["description"])
            raise Exception("Something went wrong with Telegram APIs")
        self.bot_username = info["result"]["username"]
        self.bot_name = info["result"]["first_name"]

        self.wenet_instance_url = wenet_instance_url
        self.wenet_hub_url = wenet_hub_url
        self.app_id = app_id
        self.client_secret = client_secret
        self.redirect_url = redirect_url
        self.wenet_authentication_url = wenet_authentication_url
        self.wenet_authentication_management_url = wenet_authentication_management_url
        self.task_type_id = task_type_id
        self.community_id = community_id
        self.intent_manager = IntentManagerV3()
        self.messages_lock = Lock()
        self.message_parser_for_logs = LogMessageHandler(self.app_id, "Telegram")
        # redirecting the flow in the corresponding points
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_START, self.action_start).with_rule(intent=self.INTENT_START)
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_HELP, self.handle_help).with_rule(intent=self.INTENT_HELP)
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_CANCEL, self.cancel_action).with_rule(intent=self.INTENT_CANCEL)
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_INFO, self.action_info).with_rule(intent=self.INTENT_INFO)
        )

    @abc.abstractmethod
    def action_start(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        """
        Handle the starting message
        """
        pass

    @abc.abstractmethod
    def action_info(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        """
        Handle the info message, showing the list of available commands
        """
        pass

    @abc.abstractmethod
    def action_error(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        """
        General error handler
        """
        pass

    @abc.abstractmethod
    def cancel_action(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        """
        Cancel the current operation - e.g. the ongoing creation of a task
        """
        pass

    @abc.abstractmethod
    def handle_help(self, message: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        """
        General help message
        """
        pass

    def is_user_authenticated(self, message: IncomingSocialEvent) -> bool:
        """
        Check whether the user is authenticated
        :return: True if the user is authenticated, False otherwise
        """
        return message.context.has_static_state(self.CONTEXT_WENET_USER_ID) and \
            message.context.has_static_state(self.CONTEXT_TELEGRAM_USER_ID)

    def not_authenticated_response(self, message: IncomingSocialEvent) -> OutgoingEvent:
        """
        Handle a non authenticated user
        """
        response = OutgoingEvent(social_details=message.social_details)
        response.with_context(message.context)
        url = RapidAnswerResponse(TextualResponse("Hello! Welcome WeNet. Before we start, "
                                                  "I need you to login or register into the platform"))
        url.with_option(UrlButton("Go to the WeNet Hub", self.wenet_hub_url))
        response.with_message(url)
        return response

    def handle_oauth_login(self, message: IncomingSocialEvent, _: str) -> OutgoingEvent:
        response = OutgoingEvent(social_details=message.social_details)
        response.with_message(
            TelegramTextualResponse(f"To use the bot you must first authorize access on the WeNet platform: "
                                    f"{self.wenet_authentication_url}/login?client_id={self.app_id}&external_id={message.social_details.get_user_id()}",
                                    parse_mode=None)
        )
        return response

    def _get_service_connector_from_social_details(self, social_details: TelegramDetails) -> ServiceApiInterface:
        oauth_client = Oauth2Client(self.app_id, self.client_secret, social_details.unique_id(), self.oauth_cache, token_endpoint_url=self.wenet_authentication_management_url)
        return ServiceApiInterface(oauth_client, self.wenet_instance_url)

    def _get_service_api_interface_connector_from_context(self, context: ConversationContext) -> ServiceApiInterface:
        if not context.has_static_state(self.CONTEXT_TELEGRAM_USER_ID):
            raise Exception("Missing Telegram user ID in the context")
        if not isinstance(self._connector, TelegramSocialConnector):
            raise Exception("Expected telegram social connector")
        telegram_id = context.get_static_state(self.CONTEXT_TELEGRAM_USER_ID)
        social_details = TelegramDetails(int(telegram_id), int(telegram_id),
                                         self._connector.get_telegram_bot_id())
        return self._get_service_connector_from_social_details(social_details)

    def get_user_accounts(self, wenet_id) -> List[UserConversationContext]:
        result = self._interface_connector.get_user_contexts(
            self._instance_namespace,
            self._bot_id,
            static_context_key=self.CONTEXT_WENET_USER_ID,
            static_context_value=wenet_id
        )
        logger.info(f"Retrieved [{len(result)}] user conversation context for account [{wenet_id}]")
        return result

    # handle messages coming from WeNet
    def _handle_custom_event(self, custom_event: IncomingCustomEvent):
        """
        This function handles all the incoming messages from the bot endpoint
        """
        logger.debug(f"Received event {type(custom_event)} {custom_event.to_repr()}")
        # this lock is needed to avoid that different threads write concurrently the static context,
        # in particular the oauth tokens
        self.messages_lock.acquire()
        try:
            payload = custom_event.payload
            if "type" in payload and payload["type"] == WeNetAuthenticationEvent.TYPE:
                message = WeNetAuthenticationEvent.from_repr(payload)
            elif "label" in payload:
                message = MessageBuilder.build(custom_event.payload)
            else:
                raise ValueError(f"Unable to handle an event of type [{type(custom_event)}]")

            if isinstance(message, WeNetAuthenticationEvent):
                notification = self.handle_wenet_authentication_result(message)
                self.send_notification(notification)
            else:
                # getting service api handler
                user_accounts = self.get_user_accounts(message.receiver_id)
                if len(user_accounts) != 1:
                    raise Exception(f"No context associated with Wenet user {message.receiver_id}")
                service_api = self._get_service_api_interface_connector_from_context(user_accounts[0].context)
                # logging incoming notification
                logged_notification = self.message_parser_for_logs.create_notification(message, message.receiver_id)
                try:
                    service_api.log_message(logged_notification)
                except TypeError as e:
                    logger.warning("Unsupported message to log", exc_info=e)
                except CreationError:
                    logger.warning("Unable to log the incoming message to the service API")

                if isinstance(message, TextualMessage):
                    notification = self.handle_wenet_textual_message(message, response_to=logged_notification.message_id)
                    self.send_notification(notification)
                elif isinstance(message, Message):
                    notification = self.handle_wenet_message(message, response_to=logged_notification.message_id)
                    self.send_notification(notification)
                else:
                    raise ValueError(f"Unable to handle an event of type [{type(custom_event)}]")

                # logging outgoing messages
                for outgoing_message in notification.messages:
                    try:
                        service_api.log_message(self.message_parser_for_logs.create_response(outgoing_message, user_accounts[0].context.get_static_state(self.CONTEXT_WENET_USER_ID), logged_notification.message_id))
                    except TypeError as e:
                        logger.warning("Unsupported message to log", exc_info=e)
                    except CreationError:
                        logger.warning("Unable to send logs to the service API")

                if notification.context is not None:
                    self._interface_connector.update_user_context(UserConversationContext(
                        social_details=notification.social_details,
                        context=notification.context,
                        version=UserConversationContext.VERSION_V3)
                    )
        except (KeyError, ValueError) as e:
            logger.error("Malformed message from WeNet, the parser raised the following exception: %s \n event: [%s]" % (e, custom_event.to_repr()))
        except NotFound as e:
            logger.error(e.server_response)
        except Exception as e:
            logger.exception("Unable to handle to command", exc_info=e)
        finally:
            # in any case the lock must be released, otherwise all the other messages are blocked forever
            self.messages_lock.release()

    @abc.abstractmethod
    def handle_wenet_textual_message(self, message: TextualMessage, response_to: str) -> NotificationEvent:
        """
        Handle all the incoming textual messages
        """
        pass

    @abc.abstractmethod
    def handle_wenet_message(self, message: Message, response_to: str) -> NotificationEvent:
        """
        Handle all the incoming messages (e.g. Task notifications, etc).
        """

    @abc.abstractmethod
    def handle_wenet_authentication_result(self, message: WeNetAuthenticationEvent) -> NotificationEvent:
        pass

    def _create_response(self, incoming_event: IncomingSocialEvent) -> OutgoingEvent:
        """
        General handler for all the user incoming messages
        """
        if not isinstance(incoming_event.social_details, TelegramDetails):
            raise Exception(f"Expected TelegramDetails, got {type(incoming_event.social_details)}")
        logger.debug(f"Received event {incoming_event}")
        service_api = self._get_service_connector_from_social_details(incoming_event.social_details)
        context = incoming_event.context
        if not self.is_user_authenticated(incoming_event):  # authentication adds wenet id in the context
            return self.handle_oauth_login(incoming_event, "")

        logged_incoming_message = self.message_parser_for_logs.create_request(incoming_event.incoming_message, context.get_static_state(self.CONTEXT_WENET_USER_ID))
        try:
            # logging incoming event
            try:
                service_api.log_message(logged_incoming_message)
            except TypeError as e:
                logger.warning("Unsupported message to log", exc_info=e)
            except CreationError:
                logger.warning("Unable to log the incoming message to the service API")

            incoming_event.incoming_message.message_id = logged_incoming_message.message_id  # change to this id in order to have this information in the various methods to allow to log messages related to responses sent to other users
            outgoing_event, fulfiller, satisfying_rule = self.intent_manager.manage(incoming_event)
            context.with_dynamic_state(self.PREVIOUS_INTENT, fulfiller.intent_id)
            outgoing_event.with_context(context)
        except RefreshTokenExpiredError:
            return self.handle_oauth_login(incoming_event, "")
        except Exception as e:
            logger.exception("Something went wrong while handling incoming message", exc_info=e)
            outgoing_event = self.action_error(incoming_event, "error")
        logger.debug(f"Created response {outgoing_event}")
        # logging outgoing messages
        for outgoing_message in outgoing_event.messages:
            try:
                service_api.log_message(self.message_parser_for_logs.create_response(outgoing_message, context.get_static_state(self.CONTEXT_WENET_USER_ID), logged_incoming_message.message_id))
            except TypeError as e:
                logger.warning("Unsupported message to log", exc_info=e)
            except RefreshTokenExpiredError:
                outgoing_event = self.handle_oauth_login(incoming_event, "")
            except CreationError:
                logger.warning("Unable to send logs to the service API")
        return outgoing_event

    def _save_wenet_and_telegram_user_id_to_context(self, message: WeNetAuthenticationEvent, social_details: TelegramDetails) -> None:
        """
        Get from Wenet the user ID and saves it into the context
        """
        client = Oauth2Client.initialize_with_code(
            self.app_id, self.client_secret, message.code, self.redirect_url, social_details.unique_id(),
            self.oauth_cache, token_endpoint_url=self.wenet_authentication_management_url
        )

        service_api = ServiceApiInterface(client, self.wenet_instance_url)
        context = self._interface_connector.get_user_context(social_details)
        context.context.with_static_state(self.CONTEXT_TELEGRAM_USER_ID, social_details.user_id)

        # get wenet user ID
        wenet_user_id_request = service_api.get_token_details()
        wenet_user_id = wenet_user_id_request.profile_id
        logger.debug(f"Wenet user ID is {wenet_user_id}")
        context.context.with_static_state(self.CONTEXT_WENET_USER_ID, wenet_user_id)

        self._interface_connector.update_user_context(context)

    @staticmethod
    def parse_text_with_markdown(text: str) -> str:
        """
        Given a string, replace any possible * with \u2022 (a dot), an underscore with a dash and a ` with '
        """
        text = text.replace("*", "\u2022")
        text = text.replace("_", "-")
        text = text.replace("`", "'")
        return text
