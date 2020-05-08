import logging
from typing import Optional, List
from uuid import uuid4

import requests
from emoji import emojize

from chatbot_core.model.details import TelegramDetails
from chatbot_core.model.event import IncomingSocialEvent, IncomingCustomEvent
from chatbot_core.model.message import IncomingTextMessage
from chatbot_core.nlp.handler import NLPHandler
from chatbot_core.translator.translator import Translator
from chatbot_core.v3.connector.social_connector import SocialConnector
from chatbot_core.v3.handler.event_handler import EventHandler
from chatbot_core.v3.handler.helpers.intent_manager import IntentManagerV3, IntentFulfillerV3
from chatbot_core.v3.logger.connectors.uhopper_connector import UhopperLoggerConnector
from chatbot_core.v3.logger.event_logger import LoggerConnector
from chatbot_core.v3.model.actions import UrlButton
from chatbot_core.v3.model.messages import TextualResponse, RapidAnswerResponse, TelegramTextualResponse, \
    TelegramRapidAnswerResponse
from chatbot_core.v3.model.outgoing_event import OutgoingEvent, NotificationEvent
from eat_together_bot.models import Task
from eat_together_bot.utils import Utils
from uhopper.utils.alert import AlertModule
from wenet.common.interface.exceptions import TaskNotFound, TaskCreationError, TaskTransactionCreationError
from wenet.common.interface.service_api import ServiceApiInterface
from wenet.common.model.message.builder import MessageBuilder
from wenet.common.model.message.message import TaskNotification, TextualMessage, NewUserForPlatform, \
    TaskProposalNotification, TaskVolunteerNotification, TaskSelectionNotification
from wenet.common.model.task.task import TaskAttribute, TaskGoal
from wenet.common.model.task.transaction import TaskTransaction

logger = logging.getLogger("uhopper.chatbot.wenet-eat-together-chatbot")


class EatTogetherHandler(EventHandler):
    TELEGRAM_GET_ME_API = 'https://api.telegram.org/bot{}/getMe'

    PREVIOUS_INTENT = "previous_message_intent"
    # context keys
    CONTEXT_CURRENT_STATE = "current_state"
    CONTEXT_ORGANIZE_TASK_OBJECT = 'organize_task_object'
    CONTEXT_PROPOSAL_TASK_OBJECT = 'proposal_task_object'
    CONTEXT_VOLUNTEER_CANDIDATURE_TASK_ID = 'volunteer_candidature_task_id'
    CONTEXT_PROPOSAL_USER_ID = 'proposal_user_id'
    CONTEXT_WENET_USER_ID = 'wenet_user_id'
    CONTEXT_VOLUNTEER_INFO = 'volunteer_info'
    # all the recognize intents
    INTENT_START = '/start'
    INTENT_CANCEL = '/cancel'
    INTENT_HELP = '/help'
    INTENT_ORGANIZE = '/organize'
    INTENT_CONFIRM_TASK_CREATION = 'task_creation_confirm'
    INTENT_CANCEL_TASK_CREATION = 'task_creation_cancel'
    INTENT_CONFIRM_TASK_PROPOSAL = 'task_creation_confirm'
    INTENT_CANCEL_TASK_PROPOSAL = 'task_creation_cancel'
    INTENT_VOLUNTEER_INFO = 'volunteer_info'
    INTENT_CONFIRM_VOLUNTEER_PROPOSAL = 'task_volunteer_confirm'
    INTENT_CANCEL_VOLUNTEER_PROPOSAL = 'task_volunteer_cancel'
    # task creation states (/organize command)
    ORGANIZE_Q1 = 'organize_q1'
    ORGANIZE_Q2 = 'organize_q2'
    ORGANIZE_Q3 = 'organize_q3'
    ORGANIZE_Q4 = 'organize_q4'
    ORGANIZE_Q5 = 'organize_q5'
    ORGANIZE_Q6 = 'organize_q6'
    ORGANIZE_RECAP = 'organize_recap'
    # task proposal state
    PROPOSAL = 'send_proposal'
    # volunteer candidature approval state
    VOLUNTEER_CANDIDATURE = 'volunteer_candidature'

    def __init__(self, instance_namespace: str,
                 bot_id: str,
                 handler_id: str,
                 telegram_id: str,
                 wenet_backend_url: str,
                 app_id: str,
                 wenet_hub_url: str,
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
        self.app_id = app_id
        self.wenet_hub_url = wenet_hub_url
        self.service_api = ServiceApiInterface(wenet_backend_url, app_id)
        self.intent_manager = IntentManagerV3()
        uhopper_logger_connector = UhopperLoggerConnector().with_handler(instance_namespace)
        self.with_logger_connector(uhopper_logger_connector)
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
            IntentFulfillerV3(self.ORGANIZE_Q1, self.organize_q1).with_rule(intent=self.INTENT_ORGANIZE)
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.ORGANIZE_Q2, self.organize_q2).with_rule(
                static_context=(self.CONTEXT_CURRENT_STATE, self.ORGANIZE_Q1))
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.ORGANIZE_Q3, self.organize_q3).with_rule(
                static_context=(self.CONTEXT_CURRENT_STATE, self.ORGANIZE_Q2))
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.ORGANIZE_Q4, self.organize_q4).with_rule(
                static_context=(self.CONTEXT_CURRENT_STATE, self.ORGANIZE_Q3))
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.ORGANIZE_Q5, self.organize_q5).with_rule(
                static_context=(self.CONTEXT_CURRENT_STATE, self.ORGANIZE_Q4))
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.ORGANIZE_Q6, self.organize_q6).with_rule(
                static_context=(self.CONTEXT_CURRENT_STATE, self.ORGANIZE_Q5))
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.ORGANIZE_RECAP, self.organize_recap_message).with_rule(
                static_context=(self.CONTEXT_CURRENT_STATE, self.ORGANIZE_Q6))
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_CANCEL_TASK_CREATION, self.action_cancel_task_creation).with_rule(
                intent=self.INTENT_CANCEL_TASK_CREATION,
                static_context=(self.CONTEXT_CURRENT_STATE, self.ORGANIZE_RECAP)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_CONFIRM_TASK_CREATION, self.action_confirm_task_creation).with_rule(
                intent=self.INTENT_CONFIRM_TASK_CREATION,
                static_context=(self.CONTEXT_CURRENT_STATE, self.ORGANIZE_RECAP)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_CONFIRM_TASK_PROPOSAL, self.action_confirm_task_proposal).with_rule(
                intent=self.INTENT_CONFIRM_TASK_PROPOSAL, static_context=(self.CONTEXT_CURRENT_STATE, self.PROPOSAL)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_CANCEL_TASK_PROPOSAL, self.action_delete_task_proposal).with_rule(
                intent=self.INTENT_CANCEL_TASK_PROPOSAL, static_context=(self.CONTEXT_CURRENT_STATE, self.PROPOSAL)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_VOLUNTEER_INFO, self.handle_volunteer_info).with_rule(
                intent=self.INTENT_VOLUNTEER_INFO,
                static_context=(self.CONTEXT_CURRENT_STATE, self.VOLUNTEER_CANDIDATURE)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_CONFIRM_VOLUNTEER_PROPOSAL, self.handle_confirm_candidature).with_rule(
                intent=self.INTENT_CONFIRM_VOLUNTEER_PROPOSAL,
                static_context=(self.CONTEXT_CURRENT_STATE, self.VOLUNTEER_CANDIDATURE)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_CANCEL_VOLUNTEER_PROPOSAL, self.handle_reject_candidature).with_rule(
                intent=self.INTENT_CANCEL_VOLUNTEER_PROPOSAL,
                static_context=(self.CONTEXT_CURRENT_STATE, self.VOLUNTEER_CANDIDATURE)
            )
        )

    # handle messages coming from WeNet
    def _handle_custom_event(self, custom_event: IncomingCustomEvent):
        try:
            message = MessageBuilder.build(custom_event.payload)
            if isinstance(message, TaskNotification):
                notification = self.handle_wenet_notification_message(message)
                self.send_notification(notification)
            elif isinstance(message, TextualMessage):
                self.handle_wenet_textual_message(message)
                # self.send_notification(self.handle_wenet_textual_message(message))
            elif isinstance(message, NewUserForPlatform):
                self.send_notification(self._handle_new_user_message(message))
        except (KeyError, ValueError) as e:
            logger.error("Malformed message from WeNet, the parser raised the following exception: %s" % e)
            self._alert_module.alert("Malformed message from WeNet, the parser raised the following exception", e,
                                     "WeNet eat-together telegram bot")

    def handle_wenet_textual_message(self, message: TextualMessage):  # -> NotificationEvent:
        # currently not able to handle messages between users
        logger.warning("Not able to handle messages between users")

    def handle_wenet_notification_message(self, message: TaskNotification) -> NotificationEvent:
        user_account = self.service_api.get_user_accounts(message.recipient_id)
        try:
            user_telegram_profile = Utils.extract_telegram_account(user_account)
            recipient_details = TelegramDetails(user_telegram_profile.telegram_id,
                                                user_telegram_profile.metadata["chat_id"])
            context = self._interface_connector.get_user_context(recipient_details)
            # service_api_task = self.service_api.get_task(str(message.task_id))
            # TODO ripristinare
            from wenet.common.model.task.task import Task as WenetTask
            service_api_task = WenetTask("pippo", 123456, 123456, "tasktype", "4", "1", TaskGoal("name", "descr"), 123455, 123456, 123456, [], [])
            if isinstance(message, TaskProposalNotification):
                # the system wants to propose a task to an user
                task = Task.from_service_api_task_repr(service_api_task.to_repr())
                context.context.with_static_state(self.CONTEXT_CURRENT_STATE, self.PROPOSAL)
                context.context.with_static_state(self.CONTEXT_PROPOSAL_TASK_OBJECT, task.to_repr())
                context.context.with_static_state(self.CONTEXT_PROPOSAL_USER_ID, message.recipient_id)
                self._interface_connector.update_user_context(context)
                response_message = TextualResponse("There's a task that might interest you:")
                response = RapidAnswerResponse(
                    TelegramTextualResponse(emojize(task.recap_complete(), use_aliases=True)))
                response.with_textual_option(emojize(":x: Not interested", use_aliases=True),
                                             self.INTENT_CANCEL_TASK_PROPOSAL)
                response.with_textual_option(emojize(":white_check_mark: I'm interested", use_aliases=True),
                                             self.INTENT_CONFIRM_TASK_PROPOSAL)
                return NotificationEvent(recipient_details, [response_message, response], context.context)
            elif isinstance(message, TaskVolunteerNotification):
                # a volunteer has applied to a task, and the task creator is notified
                user_object = self.service_api.get_user_profile(str(message.volunteer_id))
                if user_object is None:
                    error_message = "Error, userId [%s] does not give any user profile" % str(message.volunteer_id)
                    logger.error(error_message)
                    self._alert_module.alert(error_message)
                    raise ValueError(error_message)
                user_name = "%s %s" % (user_object.name.first, user_object.name.last)
                message_text = "%s is interested in your event: *%s*! Do you want to accept his application" \
                               % (user_name, service_api_task.goal.name)
                response = TelegramRapidAnswerResponse(TextualResponse(message_text), row_displacement=[1, 2])
                response.with_textual_option(emojize(":question: More about the volunteer", use_aliases=True),
                                             self.INTENT_VOLUNTEER_INFO)
                response.with_textual_option(emojize(":x: Not accept", use_aliases=True),
                                             self.INTENT_CANCEL_VOLUNTEER_PROPOSAL)
                response.with_textual_option(emojize(":white_check_mark: Yes, why not!?!", use_aliases=True),
                                             self.INTENT_CONFIRM_VOLUNTEER_PROPOSAL)
                context.context.with_static_state(self.CONTEXT_CURRENT_STATE, self.VOLUNTEER_CANDIDATURE)
                context.context.with_static_state(self.CONTEXT_VOLUNTEER_INFO, message.volunteer_id)
                context.context.with_static_state(self.CONTEXT_VOLUNTEER_CANDIDATURE_TASK_ID, message.task_id)
                self._interface_connector.update_user_context(context)
                return NotificationEvent(recipient_details, [response], context.context)
            elif isinstance(message, TaskSelectionNotification):
                if message.outcome == TaskSelectionNotification.OUTCOME_ACCEPTED:
                    text = ":tada: I'm happy to announce that the creator accepted you for the event: *%s*" \
                           % service_api_task.goal.name
                elif message.outcome == TaskSelectionNotification.OUTCOME_REFUSED:
                    text = "I'm very sorry :pensive:, the creator didn't accept you for the event: *%s*" \
                           % service_api_task.goal.name
                else:
                    logger.error("Outcome [%s] unrecognized" % message.outcome)
                    self._alert_module.alert("Outcome [%s] unrecognized" % message.outcome)
                    raise Exception("Outcome [%s] unrecognized" % message.outcome)
                response = TextualResponse(emojize(text, use_aliases=True))
                return NotificationEvent(recipient_details, [response])
            else:
                pass
        except TaskNotFound:
            logger.error(f"No task associated with id [{message.task_id}]")
            self._alert_module.alert(f"No task associated with id [{message.task_id}]")
        except AttributeError as e:
            logger.error("Null pointer exception. Either not able to extract a user account from Wenet id, "
                         "or no Telegram account associated")
            self._alert_module.alert("Null pointer exception. Either not able to extract a user account from Wenet id, "
                                     "or no Telegram account associated", e)
        except KeyError as e:
            logger.error("Telegram profile has not an associated chat id")
            self._alert_module.alert("Telegram profile has not an associated chat id", e)

    def _handle_new_user_message(self, message: NewUserForPlatform) -> NotificationEvent:
        user_account = self.service_api.get_user_accounts(message.user_id)
        try:
            user_telegram_profile = Utils.extract_telegram_account(user_account)
            social_details = TelegramDetails(user_telegram_profile.telegram_id, user_telegram_profile.telegram_id)
            # asking the username to Telegram
            user_name_req = requests.get("https://api.telegram.org/bot%s/getChat" % self.telegram_id,
                                         params={"chat_id": user_telegram_profile.telegram_id}).json()
            user_name = ""
            if user_name_req["ok"] and "first_name" in user_name_req["result"]:
                user_name = user_name_req["result"]["first_name"]
            response = [
                TextualResponse(emojize("Hello %s, welcome to the Wenet _eat together_ chatbot :hugging_face:"
                                        % user_name.replace("_", ""), use_aliases=True)),
                TextualResponse(emojize("Try to use one of the following commmands:\n"
                                        "`/organize` to start organizing a shared meal", use_aliases=True))
            ]
            return NotificationEvent(social_details, response)
        except AttributeError as e:
            logger.error(f"WeNet user {message.user_id} has not an associated Telegram account")
            self._alert_module.alert(f"WeNet user {message.user_id} has not an associated Telegram account", e)

    def _create_response(self, incoming_event: IncomingSocialEvent) -> OutgoingEvent:
        context = incoming_event.context
        if not self.authenticate_user(incoming_event):  # authentication adds wenet id in the context
            return self.not_authenticated_response(incoming_event)
        else:
            # updating user metadata with chat id
            if isinstance(incoming_event.social_details, TelegramDetails):
                user_metadata = {"chat_id": incoming_event.social_details.chat_id}
                wenet_id = incoming_event.context.get_static_state(self.CONTEXT_WENET_USER_ID)
                self.service_api.update_user_metadata_telegram(incoming_event.social_details.user_id, wenet_id,
                                                               user_metadata)
        try:
            outgoing_event, fulfiller, satisfying_rule = self.intent_manager.manage(incoming_event)
            context.with_dynamic_state(self.PREVIOUS_INTENT, fulfiller.intent_id)
            outgoing_event.with_context(context)
        except Exception as e:
            logger.exception("Something went wrong while handling incoming message", exc_info=e)
            outgoing_event = self._action_error(incoming_event, "error")
        return outgoing_event

    def _action_error(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_message(TextualResponse(emojize("I'm very sorry but I didn't understand :pensive:",
                                                      use_aliases=True)))
        return response

    def cancel_action(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        to_remove = [self.CONTEXT_CURRENT_STATE, self.CONTEXT_ORGANIZE_TASK_OBJECT, self.CONTEXT_PROPOSAL_TASK_OBJECT]
        context = incoming_event.context
        for context_key in to_remove:
            if context.has_static_state(context_key):
                context.delete_static_state(context_key)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_context(context)
        response.with_message(TextualResponse("Default text"))
        return response

    def action_start(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_message(TextualResponse("Try /organize"))
        return response

    def _ask_question(self, incoming_event: IncomingSocialEvent, message: str, state: str) -> OutgoingEvent:
        context = incoming_event.context
        context.with_static_state(self.CONTEXT_CURRENT_STATE, state)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_context(context)
        response.with_message(TextualResponse(emojize(message, use_aliases=True)))
        return response

    def organize_q1(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        message = ("Q1: :calendar: When do you want to organize the social meal?"
                   "(remember to specify both the date and time, in the following format: "
                   "`<YYYY> <MM> <DD> <HH> <mm>` - e.g. `2020 05 13 13 00`)")
        return self._ask_question(incoming_event, message, self.ORGANIZE_Q1)

    def organize_q2(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        if isinstance(incoming_event.incoming_message, IncomingTextMessage):
            text = incoming_event.incoming_message.text
            timestamp = Utils.parse_datetime(text)
            wenet_id = incoming_event.context.get_static_state(self.CONTEXT_WENET_USER_ID)
            if timestamp is not None:
                task = Task(str(uuid4()), wenet_id, when=timestamp)
                incoming_event.context.with_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT, task.to_repr())
                message = "Q2: :round_pushpin: Where will it take place?"
                return self._ask_question(incoming_event, message, self.ORGANIZE_Q2)
            else:
                message = ("The format you used for specifying the date and time is not valid. Please stick with: "
                           "`<YYYY> <MM> <DD> <HH> <mm>` (e.g. `2020 05 13 13 00`)")
                return self._ask_question(incoming_event, message, self.ORGANIZE_Q1)
        else:
            message = ("Please write me the date and the time of your event, "
                       "or type /cancel to cancel the current operation")
            return self._ask_question(incoming_event, message, self.ORGANIZE_Q1)

    def organize_q3(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        if isinstance(incoming_event.incoming_message, IncomingTextMessage):
            text = incoming_event.incoming_message.text
            task = Task.from_repr(incoming_event.context.get_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT))
            task.where = text
            incoming_event.context.with_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT, task.to_repr())
            message = ("Q3: :alarm_clock: By when do you want to receive applications? "
                       "Please use the following format: "
                       "`<YYYY> <mm> <dd> <HH> <MM>` - e.g. `2020 05 13 13 00`)")
            return self._ask_question(incoming_event, message, self.ORGANIZE_Q3)
        else:
            message = ("Please write me where the event will take place, "
                       "or type /cancel to cancel the current operation")
            return self._ask_question(incoming_event, message, self.ORGANIZE_Q2)

    def organize_q4(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        if isinstance(incoming_event.incoming_message, IncomingTextMessage):
            text = incoming_event.incoming_message.text
            timestamp = Utils.parse_datetime(text)
            if timestamp is not None:
                task = Task.from_repr(incoming_event.context.get_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT))
                task.application_deadline = timestamp
                incoming_event.context.with_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT, task.to_repr())
                message = "Q4: :couple: How many people can attend?"
                return self._ask_question(incoming_event, message, self.ORGANIZE_Q4)
            else:
                message = ("The format you used for specifying the date and time is not valid. Please stick with: "
                           "`<YYYY> <mm> <dd> <HH> <MM>` (e.g. `2020 05 13 13 00`)")
                return self._ask_question(incoming_event, message, self.ORGANIZE_Q3)
        else:
            message = ("Please write me by when you want to receive applications, "
                       "or type /cancel to cancel the current operation")
            return self._ask_question(incoming_event, message, self.ORGANIZE_Q3)

    def organize_q5(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        if isinstance(incoming_event.incoming_message, IncomingTextMessage):
            text = incoming_event.incoming_message.text
            task = Task.from_repr(incoming_event.context.get_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT))
            task.max_people = text
            incoming_event.context.with_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT, task.to_repr())
            message = "Q5: Name of your event:"
            return self._ask_question(incoming_event, message, self.ORGANIZE_Q5)
        else:
            message = ("Please write me how many people can attend to your event, "
                       "or type /cancel to cancel the current operation")
            return self._ask_question(incoming_event, message, self.ORGANIZE_Q4)

    def organize_q6(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        if isinstance(incoming_event.incoming_message, IncomingTextMessage):
            text = incoming_event.incoming_message.text
            task = Task.from_repr(incoming_event.context.get_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT))
            task.name = text
            incoming_event.context.with_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT, task.to_repr())
            message = "Q6: Set a description to share some more details!"
            return self._ask_question(incoming_event, message, self.ORGANIZE_Q6)
        else:
            message = ("Please write me the name of your event, "
                       "or type /cancel to cancel the current operation")
            return self._ask_question(incoming_event, message, self.ORGANIZE_Q5)

    def organize_recap_message(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        if isinstance(incoming_event.incoming_message, IncomingTextMessage):
            context = incoming_event.context
            description = incoming_event.incoming_message.text
            task = Task.from_repr(context.get_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT))
            task.description = description
            context.with_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT, task.to_repr())
            context.with_static_state(self.CONTEXT_CURRENT_STATE, self.ORGANIZE_RECAP)
            response = OutgoingEvent(social_details=incoming_event.social_details)
            response.with_context(context)
            response.with_message(TextualResponse("Super! Your event is ready, let's have a check:"))
            recap = RapidAnswerResponse(TelegramTextualResponse(emojize(task.recap_without_creator(),
                                                                        use_aliases=True)))
            recap.with_textual_option(emojize(":x: Cancel", use_aliases=True), self.INTENT_CANCEL_TASK_CREATION)
            recap.with_textual_option(emojize(":white_check_mark: Confirm", use_aliases=True),
                                      self.INTENT_CONFIRM_TASK_CREATION)
            response.with_message(recap)
            return response
        else:
            message = ("Please write me a description of your event, "
                       "or type /cancel to cancel the current operation")
            return self._ask_question(incoming_event, message, self.ORGANIZE_Q6)

    def action_cancel_task_creation(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        context = incoming_event.context
        context.delete_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT)
        context.delete_static_state(self.CONTEXT_CURRENT_STATE)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_message(TextualResponse("All the information have been discarded"))
        response.with_context(context)
        return response

    def action_confirm_task_creation(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        from wenet.common.model.task.task import Task as WenetTask
        context = incoming_event.context
        task = Task.from_repr(context.get_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT))
        context.delete_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT)
        context.delete_static_state(self.CONTEXT_CURRENT_STATE)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        try:
            # TODO capire se gli attributi vanno ad oggetto o lista
            self.service_api.create_task(WenetTask.from_repr(task.to_service_api_repr(self.app_id)))
            response.with_message(TextualResponse(emojize("Your event has been saved successfully :tada:",
                                                          use_aliases=True)))
        except TaskCreationError as e:
            logger.error("Error, unable to create a new task")
            self._alert_module.alert("Error, unable to create a new task", e)
            response.with_message(TextualResponse("I'm sorry, but something went wrong with the creation of your task."
                                                  " Try again later"))
        finally:
            response.with_context(context)
            return response

    def action_confirm_task_proposal(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        context = incoming_event.context
        if not context.has_static_state(self.CONTEXT_PROPOSAL_TASK_OBJECT):
            error_message = "Illegal state: no task object in the context when the user confirms its proposal"
            logger.error(error_message)
            self._alert_module.alert(error_message)
            raise ValueError(error_message)
        if not context.has_static_state(self.CONTEXT_PROPOSAL_USER_ID):
            error_message = "Illegal state: no volunteer id in the context when the user confirms its proposal"
            logger.error(error_message)
            self._alert_module.alert(error_message)
            raise ValueError(error_message)
        task = Task.from_repr(context.get_static_state(self.CONTEXT_PROPOSAL_TASK_OBJECT))
        volunteer_id = context.get_static_state(self.CONTEXT_PROPOSAL_USER_ID)
        context.delete_static_state(self.CONTEXT_PROPOSAL_TASK_OBJECT)
        context.delete_static_state(self.CONTEXT_PROPOSAL_USER_ID)
        context.delete_static_state(self.CONTEXT_CURRENT_STATE)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_message(TextualResponse(emojize("Great! I immediately send a notification to the task creator! "
                                                      "I'll let you know if you are selected to participate :wink:",
                                                      use_aliases=True)))
        response.with_context(context)
        transaction = TaskTransaction(task.id, TaskTransaction.LABEL_VOLUNTEER_FOR_TASK,
                                      [TaskAttribute("volunteerId", volunteer_id)])
        self.service_api.create_task_transaction(transaction)
        return response

    def action_delete_task_proposal(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        context = incoming_event.context
        context.delete_static_state(self.CONTEXT_PROPOSAL_TASK_OBJECT)
        context.delete_static_state(self.CONTEXT_CURRENT_STATE)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_message(TextualResponse(emojize("All right :+1:", use_aliases=True)))
        response.with_context(context)
        return response

    def authenticate_user(self, message: IncomingSocialEvent) -> bool:
        if isinstance(message.social_details, TelegramDetails):
            user_id = self.service_api.authenticate_telegram_user(message.social_details.user_id)
            if user_id is not None:
                message.context.with_static_state(self.CONTEXT_WENET_USER_ID, user_id)
                return True
        return False

    def not_authenticated_response(self, message: IncomingSocialEvent) -> OutgoingEvent:
        response = OutgoingEvent(social_details=message.social_details)
        response.with_context(message.context)
        url = RapidAnswerResponse(TextualResponse("Hello! Welcome to the eat together bot. Before we start, "
                                                  "I need you to login or register to WeNet"))
        url.with_option(UrlButton("Go to the WeNet Hub", self.wenet_hub_url))
        response.with_message(url)
        return response

    def handle_help(self, message: IncomingSocialEvent, _: str) -> OutgoingEvent:
        response = OutgoingEvent(social_details=message.social_details)
        help_text = (
            "These are the commands you can use with this chatbot:\n"
            "`/organize` to start organizing a shared meal\n"
            "`/cancel` to delete any operation you are currently doing"
        )
        response.with_message(TextualResponse(help_text))
        return response

    def handle_volunteer_info(self, message: IncomingSocialEvent, _: str) -> OutgoingEvent:
        if not message.context.has_static_state(self.CONTEXT_VOLUNTEER_INFO):
            error_message = "Illegal state: no info about the volunteer in the static context when asking for " \
                            "volunteer info during a candidature approval"
            logger.error(error_message)
            self._alert_module.alert(error_message)
            raise ValueError(error_message)
        user_id = message.context.get_static_state(self.CONTEXT_VOLUNTEER_INFO)
        response = OutgoingEvent(social_details=message.social_details)
        user_object = self.service_api.get_user_profile(str(user_id))
        if user_object is None:
            error_message = "Error, userId [%s] does not give any user profile" % str(user_id)
            logger.error(error_message)
            self._alert_module.alert(error_message)
            raise ValueError(error_message)
        response.with_message(TextualResponse("%s %s" % (user_object.name.first, user_object.name.last)))
        menu = RapidAnswerResponse(TextualResponse("So, what do you want to do?"))
        menu.with_textual_option(emojize(":x: Not accept", use_aliases=True),
                                 self.INTENT_CANCEL_VOLUNTEER_PROPOSAL)
        menu.with_textual_option(emojize(":white_check_mark: Yes, of course!", use_aliases=True),
                                 self.INTENT_CONFIRM_VOLUNTEER_PROPOSAL)
        response.with_message(menu)
        response.with_context(message.context)
        return response

    def _handle_volunteer_proposal(self, message: IncomingSocialEvent, decision: bool) -> bool:
        if not message.context.has_static_state(self.CONTEXT_VOLUNTEER_INFO):
            error_message = "Illegal state: no info about the volunteer in the static context when handling" \
                            " a candidature approval"
            logger.error(error_message)
            self._alert_module.alert(error_message)
            raise ValueError(error_message)
        if not message.context.has_static_state(self.CONTEXT_VOLUNTEER_CANDIDATURE_TASK_ID):
            error_message = "Illegal state: no info about the task in the static context when handling" \
                            " a candidature approval"
            logger.error(error_message)
            self._alert_module.alert(error_message)
            raise ValueError(error_message)
        volunteer_id = message.context.get_static_state(self.CONTEXT_VOLUNTEER_INFO)
        task_id = message.context.get_static_state(self.CONTEXT_VOLUNTEER_CANDIDATURE_TASK_ID)
        task_label = TaskTransaction.LABEL_ACCEPT_VOLUNTEER if decision else TaskTransaction.LABEL_REFUSE_VOLUNTEER
        transaction = TaskTransaction(task_id, task_label, [TaskAttribute("volunteerId", volunteer_id)])
        try:
            self.service_api.create_task_transaction(transaction)
            outcome = True
        except TaskTransactionCreationError:
            logger.error("Error during the creation of the task transaction")
            self._alert_module.alert("Error during the creation of the task transaction")
            outcome = False
        finally:
            message.context.delete_static_state(self.CONTEXT_VOLUNTEER_INFO)
            message.context.delete_static_state(self.CONTEXT_VOLUNTEER_CANDIDATURE_TASK_ID)
        return outcome

    def handle_confirm_candidature(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        response = OutgoingEvent(social_details=incoming_event.social_details)
        if self._handle_volunteer_proposal(incoming_event, True):
            response.with_message(TextualResponse("Great, you have accepted the volunteer!"))
        else:
            response.with_message(TextualResponse("I'm sorry, but something went wrong"))
        incoming_event.context.delete_static_state(self.CONTEXT_CURRENT_STATE)
        response.with_context(incoming_event.context)
        return response

    def handle_reject_candidature(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        response = OutgoingEvent(social_details=incoming_event.social_details)
        if self._handle_volunteer_proposal(incoming_event, False):
            response.with_message(TextualResponse("Ok, you have rejected the volunteer!"))
        else:
            response.with_message(TextualResponse("I'm sorry, but something went wrong"))
        incoming_event.context.delete_static_state(self.CONTEXT_CURRENT_STATE)
        response.with_context(incoming_event.context)
        return response
