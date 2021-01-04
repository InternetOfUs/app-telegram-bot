import json
import logging
from datetime import datetime
from typing import Optional, List

from chatbot_core.model.event import IncomingSocialEvent
from chatbot_core.model.message import IncomingTextMessage
from chatbot_core.nlp.handler import NLPHandler
from chatbot_core.translator.translator import Translator
from chatbot_core.v3.connector.social_connector import SocialConnector
from chatbot_core.v3.handler.helpers.intent_manager import IntentFulfillerV3
from chatbot_core.v3.logger.event_logger import LoggerConnector
from chatbot_core.v3.model.messages import TextualResponse, RapidAnswerResponse
from chatbot_core.v3.model.outgoing_event import OutgoingEvent, NotificationEvent
from common.wenet_event_handler import WenetEventHandler
from uhopper.utils.alert import AlertModule
from wenet.common.interface.exceptions import TaskCreationError
from wenet.common.model.message.event import WeNetAuthenticationEvent
from wenet.common.model.message.message import TextualMessage, Message
from wenet.common.model.task.task import Task, TaskGoal

logger = logging.getLogger("uhopper.chatbot.wenet.askforhelp.chatbot")


class AskForHelpHandler(WenetEventHandler):
    """
    The class that manages the Ask For Help Wenet chatbot.

    This is a DFA (deterministic finite automata), where the next action is given either by the current state,
    the intent of the incoming event or both the two things.
    """
    # context keys
    CONTEXT_CURRENT_STATE = "current_state"
    CONTEXT_DESIRED_ANSWERER = "desired_answerer"
    CONTEXT_ASKED_QUESTION = "asked_question"
    # all the recognize intents
    INTENT_QUESTION = '/question'
    INTENT_QUESTION_FIRST = '/question_first'
    INTENT_ASK_TO_DIFFERENT = "ask_to_different"
    INTENT_ASK_TO_SIMILAR = "ask_to_similar"
    INTENT_ASK_TO_ANYONE = "ask_to_anyone"
    # available states
    STATE_QUESTION_1 = "question_1"
    STATE_QUESTION_2 = "question_2"
    STATE_QUESTION_3 = "question_3"

    def __init__(self, instance_namespace: str, bot_id: str, handler_id: str, telegram_id: str, wenet_backend_url: str,
                 wenet_hub_url: str, app_id: str, client_secret: str, redirect_url: str, wenet_authentication_url: str,
                 wenet_authentication_management_url: str, task_type_id: str, alert_module: AlertModule,
                 connector: SocialConnector, nlp_handler: Optional[NLPHandler], translator: Optional[Translator],
                 delay_between_messages_sec: Optional[int] = None, delay_between_text_sec: Optional[float] = None,
                 logger_connectors: Optional[List[LoggerConnector]] = None):
        super().__init__(instance_namespace, bot_id, handler_id, telegram_id, wenet_backend_url, wenet_hub_url, app_id,
                         client_secret, redirect_url, wenet_authentication_url, wenet_authentication_management_url,
                         task_type_id, alert_module, connector, nlp_handler, translator, delay_between_messages_sec,
                         delay_between_text_sec, logger_connectors)
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_QUESTION, self.action_question).with_rule(intent=self.INTENT_QUESTION)
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_QUESTION_FIRST, self.action_question)
                .with_rule(intent=self.INTENT_QUESTION_FIRST)
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.STATE_QUESTION_1, self.action_question_2)
                .with_rule(static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_QUESTION_1))
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_ASK_TO_DIFFERENT, self.action_question_3).with_rule(
                intent=self.INTENT_ASK_TO_DIFFERENT,
                static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_QUESTION_2)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_ASK_TO_SIMILAR, self.action_question_3).with_rule(
                intent=self.INTENT_ASK_TO_SIMILAR,
                static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_QUESTION_2)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_ASK_TO_ANYONE, self.action_question_3).with_rule(
                intent=self.INTENT_ASK_TO_ANYONE,
                static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_QUESTION_2)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.STATE_QUESTION_3, self.action_question_4)
                .with_rule(static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_QUESTION_3))
        )

    def _get_user_locale(self, incoming_event: IncomingSocialEvent) -> str:
        # TODO implement this
        return 'en'

    def _get_help_and_info_message(self, locale: str) -> str:
        return self._translator.get_translation_instance(locale).with_text("info_text").translate()

    def action_info(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        user_locale = self._get_user_locale(incoming_event)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_message(TextualResponse(self._get_help_and_info_message(user_locale)))
        return response

    def action_error(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        user_locale = self._get_user_locale(incoming_event)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        message = self._translator.get_translation_instance(user_locale).with_text("error_text").translate()
        response.with_message(TextualResponse(message))
        return response

    def cancel_action(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        context_to_remove = [self.CONTEXT_CURRENT_STATE, self.CONTEXT_ASKED_QUESTION, self.CONTEXT_DESIRED_ANSWERER]
        context = incoming_event.context
        for context_key in context_to_remove:
            context.delete_static_state(context_key)
        user_locale = self._get_user_locale(incoming_event)
        message = self._translator.get_translation_instance(user_locale).with_text("cancel_text").translate()
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_message(TextualResponse(message))
        response.with_context(context)
        return response

    def handle_help(self, message: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        user_locale = self._get_user_locale(message)
        response = OutgoingEvent(social_details=message.social_details)
        response.with_message(TextualResponse(self._get_help_and_info_message(user_locale)))
        return response

    def action_start(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        user_locale = self._get_user_locale(incoming_event)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        message_1 = self._translator.get_translation_instance(user_locale).with_text("start_text_1").translate()
        message_2 = self._translator.get_translation_instance(user_locale).with_text("start_text_2").translate()
        message_3 = self._get_help_and_info_message(user_locale)
        button_text = self._translator.get_translation_instance(user_locale).with_text("start_button").translate()
        response.with_message(TextualResponse(message_1))
        response.with_message(TextualResponse(message_2))
        final_message_with_button = RapidAnswerResponse(TextualResponse(message_3))
        final_message_with_button.with_textual_option(button_text, self.INTENT_QUESTION_FIRST)
        response.with_message(final_message_with_button)
        return response

    def _get_command_list(self) -> str:
        return self._translator.get_translation_instance('en').with_text("info_text").translate()

    def handle_wenet_textual_message(self, message: TextualMessage) -> NotificationEvent:
        pass

    def handle_wenet_message(self, message: Message) -> NotificationEvent:
        pass

    def handle_wenet_authentication_result(self, message: WeNetAuthenticationEvent) -> NotificationEvent:
        # get and put wenet user id into context here
        pass

    def action_question(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        """
        Beginning of the /question command
        """
        context = incoming_event.context
        context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_QUESTION_1)
        user_locale = self._get_user_locale(incoming_event)
        preamble_message = None
        if intent == self.INTENT_QUESTION_FIRST:
            preamble_message = self._translator.get_translation_instance(user_locale).with_text("question_0").translate()
        message = self._translator.get_translation_instance(user_locale).with_text("question_1").translate()
        response = OutgoingEvent(social_details=incoming_event.social_details)
        if preamble_message:
            response.with_message(TextualResponse(preamble_message))
        response.with_message(TextualResponse(message))
        response.with_context(context)
        return response

    def action_question_2(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        Either ask for the person that should answer the question, or tell the user to be more inclusive
        """
        response = OutgoingEvent(social_details=incoming_event.social_details)
        user_locale = self._get_user_locale(incoming_event)
        if isinstance(incoming_event.incoming_message, IncomingTextMessage):
            question = incoming_event.incoming_message.text
            context = incoming_event.context
            context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_QUESTION_2)
            context.with_static_state(self.CONTEXT_ASKED_QUESTION, question)
            message = self._translator.get_translation_instance(user_locale).with_text("question_2").translate()
            button_1_text = self._translator.get_translation_instance(user_locale).with_text("type_answer_1").translate()
            button_2_text = self._translator.get_translation_instance(user_locale).with_text("type_answer_2").translate()
            button_3_text = self._translator.get_translation_instance(user_locale).with_text("type_answer_3").translate()
            response_with_buttons = RapidAnswerResponse(TextualResponse(message))
            response_with_buttons.with_textual_option(button_1_text, self.INTENT_ASK_TO_DIFFERENT)
            response_with_buttons.with_textual_option(button_2_text, self.INTENT_ASK_TO_SIMILAR)
            response_with_buttons.with_textual_option(button_3_text, self.INTENT_ASK_TO_ANYONE)
            response.with_message(response_with_buttons)
            response.with_context(context)
        else:
            error_message = self._translator.get_translation_instance(user_locale).with_text("question_is_not_text").translate()
            response.with_message(TextualResponse(error_message))
        return response

    def action_question_3(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        """
        Save the type of desired answerer, and ask for some more details about her. The intent contains the desired answerer
        """
        user_locale = self._get_user_locale(incoming_event)
        context = incoming_event.context
        context.with_static_state(self.CONTEXT_DESIRED_ANSWERER, intent)
        context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_QUESTION_3)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_context(context)
        message = self._translator.get_translation_instance(user_locale).with_text("specify_answerer").translate()
        response.with_message(TextualResponse(message))
        return response

    def action_question_4(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        Conclude the /question flow, with a final message
        """
        if incoming_event.context is not None:
            service_api = self._get_service_api_interface_connector_from_context(incoming_event.context)
        else:
            raise Exception(f"Missing conversation context for event {incoming_event}")
        user_locale = self._get_user_locale(incoming_event)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        if isinstance(incoming_event.incoming_message, IncomingTextMessage):
            context = incoming_event.context
            if not context.has_static_state(self.CONTEXT_ASKED_QUESTION) or not context.has_static_state(self.CONTEXT_DESIRED_ANSWERER):
                raise Exception(f"Expected {self.CONTEXT_ASKED_QUESTION} and {self.CONTEXT_DESIRED_ANSWERER} in the context")
            answerer_details = incoming_event.incoming_message.text
            wenet_id = context.get_static_state(self.CONTEXT_WENET_USER_ID)
            question = context.get_static_state(self.CONTEXT_ASKED_QUESTION)
            desired_answerer = context.get_static_state(self.CONTEXT_DESIRED_ANSWERER)
            attributes = {
                "kindOfAnswerer": desired_answerer,
                "answeredDetails": answerer_details,
            }
            question_task = Task(
                None,
                int(datetime.now().timestamp()),
                int(datetime.now().timestamp()),
                str(self.task_type_id),
                str(wenet_id),
                self.app_id,
                None,
                TaskGoal(question, ""),
                [],
                attributes,
                None,
                []
            )
            try:
                service_api.create_task(question_task)
                logger.debug(f"User [{wenet_id}] asked a question. Task created successfully")
                message = self._translator.get_translation_instance(user_locale).with_text("question_4").translate()
                response.with_message(TextualResponse(message))
            except TaskCreationError as e:
                logger.error(f"The service API responded with code {e.http_status} and message {json.dumps(e.json_response)}")
                message = self._translator.get_translation_instance(user_locale).with_text("error_task_creation").translate()
                response.with_message(TextualResponse(message))
            finally:
                context.delete_static_state(self.CONTEXT_ASKED_QUESTION)
                context.delete_static_state(self.CONTEXT_DESIRED_ANSWERER)
                context = self._save_updated_token(context, service_api.client)
                response.with_context(context)
        else:
            error_message = self._translator.get_translation_instance(user_locale).with_text("answerer_details_are_not_text").translate()
            response.with_message(TextualResponse(error_message))
        return response
