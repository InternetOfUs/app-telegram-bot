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
from chatbot_core.v3.handler.event_handler import EventHandler
from chatbot_core.v3.handler.helpers.intent_manager import IntentManagerV3, IntentFulfillerV3
from chatbot_core.v3.logger.event_logger import LoggerConnector
from chatbot_core.v3.model.actions import UrlButton
from chatbot_core.v3.model.messages import RapidAnswerResponse, TextualResponse, TelegramTextualResponse
from chatbot_core.v3.model.outgoing_event import OutgoingEvent, NotificationEvent
from uhopper.utils.alert import AlertModule
from wenet.common.interface.client import Oauth2Client
from wenet.common.interface.exceptions import TaskNotFound, RefreshTokenExpiredError
from wenet.common.interface.service_api import ServiceApiInterface
from wenet.common.model.message.builder import MessageBuilder
from wenet.common.model.message.message import TaskNotification, TextualMessage, WeNetAuthentication

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
    - _get_command_list() -> str:

    Attributes:
        - instance_namespace, bot_id, handler_id, alert_module, connector, nlp_handler, translator,
        delay_between_messages_sec, delay_between_text_sec, logger_connectors as the normal EventHandler
        - telegram_id: telegram secret code to communicate with Telegram APIs
        - wenet_backend_url: the url of the Wenet API
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
    CONTEXT_WENET_USER_ID = 'wenet_user_id'
    CONTEXT_ACCESS_TOKEN = 'access_token'
    CONTEXT_REFRESH_TOKEN = 'refresh_token'
    # all the recognize intents
    INTENT_START = '/start'
    INTENT_CANCEL = '/cancel'
    INTENT_HELP = '/help'
    INTENT_INFO = '/info'

    def __init__(self,
                 instance_namespace: str,
                 bot_id: str,
                 handler_id: str,
                 telegram_id: str,
                 wenet_backend_url: str,
                 wenet_hub_url: str,
                 app_id: str,
                 client_secret: str,
                 redirect_url: str,
                 wenet_authentication_url: str,
                 wenet_authentication_management_url: str,
                 task_type_id: str,
                 alert_module: AlertModule,
                 connector: SocialConnector,
                 nlp_handler: Optional[NLPHandler],
                 translator: Optional[Translator],
                 delay_between_messages_sec: Optional[int] = None,
                 delay_between_text_sec: Optional[float] = None,
                 logger_connectors: Optional[List[LoggerConnector]] = None):
        super().__init__(instance_namespace, bot_id, handler_id, alert_module, connector, nlp_handler, translator,
                         delay_between_messages_sec, delay_between_text_sec, logger_connectors)
        self.telegram_id = telegram_id
        # getting information about the bot
        info = requests.get(self.TELEGRAM_GET_ME_API.format(self.telegram_id)).json()
        if not info["ok"]:
            logger.error("Not able to get bot's info, Telegram APIs returned: %s" % info["description"])
            raise Exception("Something went wrong with Telegram APIs")
        self.bot_username = info["result"]["username"]
        self.bot_name = info["result"]["first_name"]

        self.wenet_backend_url = wenet_backend_url
        self.wenet_hub_url = wenet_hub_url
        self.app_id = app_id
        self.client_secret = client_secret
        self.redirect_url = redirect_url
        self.wenet_authentication_url = wenet_authentication_url
        self.wenet_authentication_management_url = wenet_authentication_management_url
        self.task_type_id = task_type_id
        self.intent_manager = IntentManagerV3()
        self.messages_lock = Lock()
        # redirecting the flow in the corresponding points
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_START, self.action_info).with_rule(intent=self.INTENT_START)
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3("TOKEN", self.handle_oauth_login).with_rule(
                static_context=(self.CONTEXT_ACCESS_TOKEN, None))
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

    def authenticate_user(self, message: IncomingSocialEvent) -> bool:
        """
        Check whether the user is authenticated
        :return: True if the user is authenticated, False otherwise
        """
        return message.context.has_static_state(self.CONTEXT_WENET_USER_ID) and message.context.has_static_state(self.CONTEXT_ACCESS_TOKEN) and message.context.has_static_state(self.CONTEXT_REFRESH_TOKEN)

    def not_authenticated_response(self, message: IncomingSocialEvent) -> OutgoingEvent:
        """
        Handle a non authenticated user
        """
        response = OutgoingEvent(social_details=message.social_details)
        response.with_context(message.context)
        url = RapidAnswerResponse(TextualResponse("Hello! Welcome to the eat together bot. Before we start, "
                                                  "I need you to login or register to WeNet"))
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
        context = self._interface_connector.get_user_context(social_details)
        return self._get_service_api_interface_connector_from_context(context.context)

    def _get_service_api_interface_connector_from_context(self, context: ConversationContext) -> ServiceApiInterface:
        if not context.has_static_state(self.CONTEXT_ACCESS_TOKEN) or not context.has_static_state(self.CONTEXT_REFRESH_TOKEN):
            raise Exception("Missing refresh or access token")
        token = context.get_static_state(self.CONTEXT_ACCESS_TOKEN, None)
        refresh_token = context.get_static_state(self.CONTEXT_REFRESH_TOKEN, None)
        oauth_client = Oauth2Client.initialize_with_token(self.wenet_authentication_management_url, self.app_id, self.client_secret, token, refresh_token)
        return ServiceApiInterface(self.wenet_backend_url, oauth_client)

    def _save_updated_token(self, context: ConversationContext, client: Oauth2Client) -> ConversationContext:
        logger.info("Saving client status")
        context.with_static_state(self.CONTEXT_ACCESS_TOKEN, client.token)
        context.with_static_state(self.CONTEXT_REFRESH_TOKEN, client.refresh_token)
        return context

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
            message = MessageBuilder.build(custom_event.payload)
            if isinstance(message, TaskNotification):
                notification = self.handle_wenet_notification_message(message)
                self.send_notification(notification)
            elif isinstance(message, TextualMessage):
                notification = self.handle_wenet_textual_message(message)
                self.send_notification(notification)
            elif isinstance(message, WeNetAuthentication):
                notification = self.handle_wenet_authentication_result(message)
                self.send_notification(notification)
            else:
                raise ValueError(f"Unable to handle an event of type [{type(custom_event)}]")

            if notification.context is not None:
                self._interface_connector.update_user_context(UserConversationContext(
                    notification.social_details,
                    context=notification.context,
                    version=UserConversationContext.VERSION_V3)
                )
        except (KeyError, ValueError) as e:
            logger.error(
                "Malformed message from WeNet, the parser raised the following exception: %s \n event: [%s]" % (
                e, custom_event.to_repr()))
        except TaskNotFound as e:
            logger.error(e.message)
        except Exception as e:
            logger.exception("Unable to handle to command", exc_info=e)
        finally:
            # in any case the lock must be released, otherwise all the other messages are blocked forever
            self.messages_lock.release()

    @abc.abstractmethod
    def handle_wenet_textual_message(self, message: TextualMessage) -> NotificationEvent:
        """
        Handle all the incoming textual messages
        """
        pass

    @abc.abstractmethod
    def handle_wenet_notification_message(self, message: TaskNotification) -> NotificationEvent:
        """
        Handle all the incoming notifications.
        """

    @abc.abstractmethod
    def handle_wenet_authentication_result(self, message: WeNetAuthentication) -> NotificationEvent:
        pass

    @staticmethod
    @abc.abstractmethod
    def _get_command_list() -> str:
        """
        :return: a markdown string with all the commands available in the chatbot
        """
        pass

    def _create_response(self, incoming_event: IncomingSocialEvent) -> OutgoingEvent:
        """
        General handler for all the user incoming messages
        """
        logger.debug(f"Received event {incoming_event}")
        context = incoming_event.context
        if not self.authenticate_user(incoming_event):  # authentication adds wenet id in the context
            return self.handle_oauth_login(incoming_event, "")
        try:
            outgoing_event, fulfiller, satisfying_rule = self.intent_manager.manage(incoming_event)
            context.with_dynamic_state(self.PREVIOUS_INTENT, fulfiller.intent_id)
            outgoing_event.with_context(context)
        except RefreshTokenExpiredError:
            logger.exception("Refresh token is not longer valid")
            outgoing_event = OutgoingEvent(social_details=incoming_event.social_details)
            outgoing_event.with_message(
                TelegramTextualResponse(f"Sorry, the login credential are not longer valid, please perform the login again in order to continue to use the bot:\n {self.wenet_authentication_url}/login?client_id={self.app_id}&external_id={incoming_event.social_details.get_user_id()}", parse_mode=None)
            )
        except Exception as e:
            logger.exception("Something went wrong while handling incoming message", exc_info=e)
            outgoing_event = self.action_error(incoming_event, "error")
        logger.debug(f"Created response {outgoing_event}")
        return outgoing_event
