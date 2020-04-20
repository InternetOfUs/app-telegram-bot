import logging
from typing import Optional, List

from emoji import emojize

from chatbot_core.model.event import IncomingSocialEvent, IncomingCustomEvent
from chatbot_core.model.message import IncomingTextMessage
from chatbot_core.nlp.handler import NLPHandler
from chatbot_core.translator.translator import Translator
from chatbot_core.v3.connector.social_connector import SocialConnector
from chatbot_core.v3.handler.event_handler import EventHandler
from chatbot_core.v3.handler.helpers.intent_manager import IntentManagerV3, IntentFulfillerV3
from chatbot_core.v3.logger.connectors.uhopper_connector import UhopperLoggerConnector
from chatbot_core.v3.logger.event_logger import LoggerConnector
from chatbot_core.v3.model.messages import TextualResponse, RapidAnswerResponse, TelegramTextualResponse
from chatbot_core.v3.model.outgoing_event import OutgoingEvent, NotificationEvent
from eat_together_bot.models import Task
from uhopper.utils.alert import AlertModule
from wenet.common.messages.builder import MessageBuilder
from wenet.common.messages.models import TaskNotification, TextualMessage

logger = logging.getLogger("uhopper.chatbot.wenet-eat-together-chatbot")


class EatTogetherHandler(EventHandler):
    PREVIOUS_INTENT = "previous_message_intent"
    # context keys
    CONTEXT_CURRENT_STATE = "current_state"
    CONTEXT_ORGANIZE_TASK_OBJECT = 'organize_task_object'
    # all the recognize intents
    INTENT_START = '/start'
    INTENT_CANCEL = '/cancel'
    INTENT_ORGANIZE = '/organize'
    INTENT_CONFIRM_TASK_CREATION = 'task_creation_confirm'
    INTENT_CANCEL_TASK_CREATION = 'task_creation_cancel'
    # task creation states (/organize command)
    ORGANIZE_Q1 = 'organize_q1'
    ORGANIZE_Q2 = 'organize_q2'
    ORGANIZE_Q3 = 'organize_q3'
    ORGANIZE_Q4 = 'organize_q4'
    ORGANIZE_Q5 = 'organize_q5'
    ORGANIZE_Q6 = 'organize_q6'
    ORGANIZE_RECAP = 'organize_recap'

    def __init__(self, instance_namespace: str, bot_id: str, handler_id: str, alert_module: AlertModule,
                 connector: SocialConnector, nlp_handler: Optional[NLPHandler], translator: Optional[Translator],
                 delay_between_messages_sec: Optional[int] = None, delay_between_text_sec: Optional[float] = None,
                 logger_connectors: Optional[List[LoggerConnector]] = None):
        super().__init__(instance_namespace, bot_id, handler_id, alert_module, connector, nlp_handler, translator,
                         delay_between_messages_sec, delay_between_text_sec, logger_connectors)
        self.intent_manager = IntentManagerV3()
        uhopper_logger_connector = UhopperLoggerConnector().with_handler("%s" % instance_namespace)
        self.with_logger_connector(uhopper_logger_connector)
        # redirecting the flow in the corresponding points
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_START, self.action_start).with_rule(intent=self.INTENT_START)
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

    # handle messages coming from WeNet
    def _handle_custom_event(self, custom_event: IncomingCustomEvent):
        print("Custom event " + str(custom_event.to_repr()))
        try:
            message = MessageBuilder.build(custom_event.payload)
            if isinstance(message, TaskNotification):
                # self.send_notification(self.handle_wenet_notification_message(message))
                pass
            elif isinstance(message, TextualMessage):
                # self.send_notification(self.handle_wenet_textual_message(message))
                pass
        except (KeyError, ValueError) as e:
            logger.error("Malformed message from WeNet, the parser raised the following exception: %s" % e)
            self._alert_module.alert("Malformed message from WeNet, the parser raised the following exception", e,
                                     "WeNet eat-together telegram bot")

    def handle_wenet_textual_message(self, message: TextualMessage) -> NotificationEvent:
        pass

    def handle_wenet_notification_message(self, message: TaskNotification) -> NotificationEvent:
        pass

    def _create_response(self, incoming_event: IncomingSocialEvent) -> OutgoingEvent:
        context = incoming_event.context
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
        to_remove = [self.CONTEXT_CURRENT_STATE, self.CONTEXT_ORGANIZE_TASK_OBJECT]
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
                   "(remember to specify both the date and time)")
        return self._ask_question(incoming_event, message, self.ORGANIZE_Q1)

    def organize_q2(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        if isinstance(incoming_event.incoming_message, IncomingTextMessage):
            text = incoming_event.incoming_message.text
            task = Task(when=text)
            incoming_event.context.with_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT, task.to_repr())
            message = "Q2: :round_pushpin: Where will it take place?"
            return self._ask_question(incoming_event, message, self.ORGANIZE_Q2)
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
            message = "Q3: :alarm_clock: By when do you want to receive applications?"
            return self._ask_question(incoming_event, message, self.ORGANIZE_Q3)
        else:
            message = ("Please write me where the event will take place, "
                       "or type /cancel to cancel the current operation")
            return self._ask_question(incoming_event, message, self.ORGANIZE_Q2)

    def organize_q4(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        if isinstance(incoming_event.incoming_message, IncomingTextMessage):
            text = incoming_event.incoming_message.text
            task = Task.from_repr(incoming_event.context.get_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT))
            task.application_deadline = text
            incoming_event.context.with_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT, task.to_repr())
            message = "Q4: :couple: How many people can attend?"
            return self._ask_question(incoming_event, message, self.ORGANIZE_Q4)
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
        context = incoming_event.context
        context.delete_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT)
        context.delete_static_state(self.CONTEXT_CURRENT_STATE)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_message(TextualResponse(emojize("Your event has been saved successfully :tada:", use_aliases=True)))
        response.with_context(context)
        return response
