import json
import logging
from datetime import datetime
from typing import Optional, List

from chatbot_core.model.event import IncomingSocialEvent
from chatbot_core.model.message import IncomingTextMessage
from chatbot_core.model.user_context import UserConversationContext
from chatbot_core.nlp.handler import NLPHandler
from chatbot_core.translator.translator import Translator
from chatbot_core.v3.connector.social_connector import SocialConnector
from chatbot_core.v3.handler.helpers.intent_manager import IntentFulfillerV3
from chatbot_core.v3.logger.event_logger import LoggerConnector
from chatbot_core.v3.model.messages import TextualResponse, RapidAnswerResponse, TelegramRapidAnswerResponse, \
    UrlImageResponse
from chatbot_core.v3.model.outgoing_event import OutgoingEvent, NotificationEvent
from common.wenet_event_handler import WenetEventHandler
from uhopper.utils.alert import AlertModule
from wenet.common.interface.exceptions import TaskCreationError, RefreshTokenExpiredError, TaskTransactionCreationError, \
    TaskNotFound
from wenet.common.model.message.event import WeNetAuthenticationEvent
from wenet.common.model.message.message import TextualMessage, Message, QuestionToAnswerMessage, \
    AnsweredQuestionMessage, IncentiveMessage, IncentiveBadge
from wenet.common.model.task.task import Task, TaskGoal
from wenet.common.model.task.transaction import TaskTransaction

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
    CONTEXT_QUESTION_TO_ANSWER = "question_to_answer"
    CONTEXT_MESSAGE_TO_REPORT = "message_to_report"
    CONTEXT_REPORTING_IS_QUESTION = "reporting_is_question"
    CONTEXT_REPORTING_REASON = "reporting_reason"
    CONTEXT_ORIGINAL_QUESTION_REPORTING = "original_question_reporting"
    CONTEXT_PROPOSED_TASKS = "proposed_tasks"
    # all the recognize intents
    INTENT_QUESTION = '/question'
    INTENT_QUESTION_FIRST = '/question_first'
    INTENT_ASK_TO_DIFFERENT = "ask_to_different"
    INTENT_ASK_TO_SIMILAR = "ask_to_similar"
    INTENT_ASK_TO_ANYONE = "ask_to_anyone"
    INTENT_ANSWER_QUESTION = "answer_question"
    INTENT_ANSWER_REMIND_LATER = "answer_remind_later"
    INTENT_ANSWER_NOT = "answer_not"
    INTENT_QUESTION_REPORT = "question_report"
    INTENT_REPORT_ABUSIVE = "abusive"
    INTENT_REPORT_SPAM = "spam"
    INTENT_ASK_MORE_ANSWERS = "ask_more_answers"
    INTENT_ANSWER_REPORT = "answer_report"
    INTENT_ANSWER = "/answer"
    INTENT_ANSWER_PICKED_QUESTION = "answering-{}"
    # available states
    STATE_QUESTION_1 = "question_1"
    STATE_QUESTION_2 = "question_2"
    STATE_QUESTION_3 = "question_3"
    STATE_ANSWER_1 = "answer_1"
    STATE_ANSWER_2 = "answer_2"
    STATE_REPORT_1 = "report_1"
    STATE_REPORT_2 = "report_2"
    STATE_RECEIVED_ANSWER = "received_answer"
    STATE_ANSWERING = "answering"
    # transaction labels
    LABEL_ANSWER_TRANSACTION = "answerTransaction"
    LABEL_NOT_ANSWER_TRANSACTION = "notAnswerTransaction"
    LABEL_REPORT_QUESTION_TRANSACTION = "reportQuestionTransaction"
    LABEL_REPORT_ANSWER_TRANSACTION = "reportAnswerTransaction"
    LABEL_MORE_ANSWER_TRANSACTION = "moreAnswerTransaction"

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
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_ANSWER_QUESTION, self.action_answer_question).with_rule(
                intent=self.INTENT_ANSWER_QUESTION,
                static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_ANSWER_1)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_ANSWER_PICKED_QUESTION, self.action_answer_question).with_rule(
                static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_ANSWERING)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3("", self.action_answer_question_2).with_rule(
                static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_ANSWER_2)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_ANSWER_NOT, self.action_not_answer_question).with_rule(
                intent=self.INTENT_ANSWER_NOT,
                static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_ANSWER_1)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_ANSWER_REMIND_LATER, self.action_answer_remind_later).with_rule(
                intent=self.INTENT_ANSWER_REMIND_LATER,
                static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_ANSWER_1)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_QUESTION_REPORT, self.action_report_message).with_rule(
                intent=self.INTENT_QUESTION_REPORT,
                static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_ANSWER_1)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_ANSWER_REPORT, self.action_report_message).with_rule(
                intent=self.INTENT_ANSWER_REPORT,
                static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_RECEIVED_ANSWER)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_REPORT_ABUSIVE, self.action_report_message_1).with_rule(
                intent=self.INTENT_REPORT_ABUSIVE,
                static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_REPORT_1)
            ).with_rule(
                intent=self.INTENT_REPORT_SPAM,
                static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_REPORT_1)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3("", self.action_report_message_2).with_rule(
                static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_REPORT_2)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_ASK_MORE_ANSWERS, self.action_more_answers).with_rule(
                intent=self.INTENT_ASK_MORE_ANSWERS,
                static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_RECEIVED_ANSWER)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_ANSWER, self.action_answer).with_rule(intent=self.INTENT_ANSWER)
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
        context_to_remove = [self.CONTEXT_CURRENT_STATE, self.CONTEXT_ASKED_QUESTION, self.CONTEXT_DESIRED_ANSWERER,
                             self.CONTEXT_QUESTION_TO_ANSWER, self.CONTEXT_MESSAGE_TO_REPORT,
                             self.CONTEXT_REPORTING_IS_QUESTION, self.CONTEXT_REPORTING_REASON,
                             self.CONTEXT_ORIGINAL_QUESTION_REPORTING]
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
        # new question to answer, or a new answer to a question
        # incentive messages or badges
        user_accounts = self.get_user_accounts(message.receiver_id)
        if len(user_accounts) != 1:
            raise Exception(f"No context associated with Wenet user {message.receiver_id}")

        user_account = user_accounts[0]
        context = user_account.context
        service_api = self._get_service_api_interface_connector_from_context(context)
        try:
            user_object = service_api.get_user_profile(str(message.receiver_id))
            if isinstance(message, QuestionToAnswerMessage):
                question_id = message.task_id
                context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_ANSWER_1)
                context.with_static_state(self.CONTEXT_QUESTION_TO_ANSWER, question_id)
                questioning_user = service_api.get_user_profile(str(message.user_id))
                message_string = self._translator.get_translation_instance(user_object.locale)\
                    .with_text("answer_message_0")\
                    .with_substitution("question", message.question)\
                    .with_substitution("user", questioning_user.name.first)\
                    .translate()
                response = TelegramRapidAnswerResponse(TextualResponse(message_string), row_displacement=[2, 2])
                response.with_textual_option(self._translator.get_translation_instance(user_object.locale).with_text("answer_question_button").translate(), self.INTENT_ANSWER_QUESTION)
                response.with_textual_option(self._translator.get_translation_instance(user_object.locale).with_text("answer_remind_later_button").translate(), self.INTENT_ANSWER_REMIND_LATER)
                response.with_textual_option(self._translator.get_translation_instance(user_object.locale).with_text("answer_not_button").translate(), self.INTENT_ANSWER_NOT)
                response.with_textual_option(self._translator.get_translation_instance(user_object.locale).with_text("answer_report_button").translate(), self.INTENT_QUESTION_REPORT)
                self._interface_connector.update_user_context(UserConversationContext(
                    social_details=user_account.social_details,
                    context=context,
                    version=UserConversationContext.VERSION_V3
                ))
                context = self._save_updated_token(context, service_api.client)
                return NotificationEvent(user_account.social_details, [response], context)
            elif isinstance(message, AnsweredQuestionMessage):
                answerer_id = message.user_id
                answer_text = message.answer
                answerer_user = service_api.get_user_profile(str(answerer_id))
                try:
                    question_task = service_api.get_task(message.task_id)
                    question_text = question_task.goal.name
                    message_string = self._translator.get_translation_instance(user_object.locale) \
                        .with_text("new_answer_message") \
                        .with_substitution("question", question_text) \
                        .with_substitution("answer", answer_text) \
                        .with_substitution("username", answerer_user.name.first) \
                        .translate()
                    answer = RapidAnswerResponse(TextualResponse(message_string))
                    button_report_text = self._translator.get_translation_instance(user_object.locale).with_text("answer_report_button").translate()
                    button_more_answers_text = self._translator.get_translation_instance(user_object.locale).with_text("more_answers_button").translate()
                    answer.with_textual_option(button_more_answers_text, self.INTENT_ASK_MORE_ANSWERS)
                    answer.with_textual_option(button_report_text, self.INTENT_ANSWER_REPORT)
                    context.with_static_state(self.CONTEXT_MESSAGE_TO_REPORT, message.transaction_id)
                    context.with_static_state(self.CONTEXT_ORIGINAL_QUESTION_REPORTING, question_task.task_id)
                    context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_RECEIVED_ANSWER)
                    self._interface_connector.update_user_context(UserConversationContext(
                        social_details=user_account.social_details,
                        context=context,
                        version=UserConversationContext.VERSION_V3
                    ))
                    context = self._save_updated_token(context, service_api.client)
                    return NotificationEvent(user_account.social_details, [answer], context)
                except TaskNotFound as e:
                    logger.error(e.message)
                    raise Exception(e.message)
            elif isinstance(message, IncentiveMessage):
                answer = TextualResponse(message.content)
                context = self._save_updated_token(context, service_api.client)
                return NotificationEvent(user_account.social_details, [answer], context)
            elif isinstance(message, IncentiveBadge):
                answer = TextualResponse(message.message)
                image = UrlImageResponse(message.image_url)
                context = self._save_updated_token(context, service_api.client)
                return NotificationEvent(user_account.social_details, [answer, image], context)
            else:
                logger.warning(f"Received unrecognized message of type {type(message)}: {message.to_repr()}")
                raise Exception()
        except RefreshTokenExpiredError:
            logger.exception("Refresh token is not longer valid")
            notification_event = NotificationEvent(social_details=user_account.social_details)
            notification_event.with_message(
                TextualResponse(
                    f"Sorry, the login credential are no longer valid, please login again in order to continue to use the bot:\n "
                    f"{self.wenet_authentication_url}/login?client_id={self.app_id}&external_id={user_account.social_details.get_user_id()}"
                )
            )
            return notification_event

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
            response_with_buttons = TelegramRapidAnswerResponse(TextualResponse(message), row_displacement=[1, 1, 1])
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

    def action_answer_question(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        """
        QuestionToAnswerMessage flow, when user click on the answer button
        """
        user_locale = self._get_user_locale(incoming_event)
        context = incoming_event.context
        context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_ANSWER_2)
        if intent.startswith(self.INTENT_ANSWER_PICKED_QUESTION):
            question_index = int(incoming_event.incoming_message.intent.value.split("-")[1])
            if not context.has_static_state(self.CONTEXT_PROPOSED_TASKS):
                error_message = "Illegal state, expected the proposed question ID in the context, but it does not exist"
                logger.error(error_message)
                raise ValueError(error_message)
            proposed_questions = context.get_static_state(self.CONTEXT_PROPOSED_TASKS)
            context.with_static_state(self.CONTEXT_QUESTION_TO_ANSWER, proposed_questions[question_index])
            context.delete_static_state(self.CONTEXT_PROPOSED_TASKS)
        message = self._translator.get_translation_instance(user_locale).with_text("question_0").translate()
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_context(context)
        response.with_message(TextualResponse(message))
        return response

    def action_answer_question_2(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        QuestionToAnswerMessage flow, collect the user's answer and thank her
        """
        if incoming_event.context is not None:
            service_api = self._get_service_api_interface_connector_from_context(incoming_event.context)
        else:
            raise Exception(f"Missing conversation context for event {incoming_event}")

        user_locale = self._get_user_locale(incoming_event)
        context = incoming_event.context
        if not context.has_static_state(self.CONTEXT_QUESTION_TO_ANSWER):
            error_message = "Illegal state, expected the question ID in the context, but it does not exist"
            logger.error(error_message)
            raise ValueError(error_message)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        if isinstance(incoming_event.incoming_message, IncomingTextMessage):
            question_id = context.get_static_state(self.CONTEXT_QUESTION_TO_ANSWER)
            answer = incoming_event.incoming_message.text
            actioneer_id = context.get_static_state(self.CONTEXT_WENET_USER_ID)
            try:
                transaction = TaskTransaction(None, question_id, self.LABEL_ANSWER_TRANSACTION,
                                              int(datetime.now().timestamp()), int(datetime.now().timestamp()),
                                              actioneer_id, {"answer": answer}, [])
                service_api.create_task_transaction(transaction)
                logger.info("Sent task transaction: %s" % str(transaction.to_repr()))
                message = self._translator.get_translation_instance(user_locale).with_text("answered_message").translate()
                response.with_message(TextualResponse(message))
            except TaskTransactionCreationError as e:
                response.with_message(TextualResponse("I'm sorry, something went wrong, try again later"))
                logger.error(
                    "Error in the creation of the transaction for answering the task [%s]. The service API resonded with code %d and message %s"
                    % (question_id, e.http_status, json.dumps(e.json_response)))
            finally:
                context.delete_static_state(self.CONTEXT_QUESTION_TO_ANSWER)
                context.delete_static_state(self.CONTEXT_CURRENT_STATE)
                context = self._save_updated_token(context, service_api.client)
                response.with_context(context)
        else:
            error_message = self._translator.get_translation_instance(user_locale).with_text("answerer_is_not_text").translate()
            response.with_message(TextualResponse(error_message))
        return response

    def action_not_answer_question(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        response = OutgoingEvent(social_details=incoming_event.social_details)
        user_locale = self._get_user_locale(incoming_event)
        if incoming_event.context is not None:
            service_api = self._get_service_api_interface_connector_from_context(incoming_event.context)
        else:
            raise Exception(f"Missing conversation context for event {incoming_event}")
        context = incoming_event.context
        if not context.has_static_state(self.CONTEXT_QUESTION_TO_ANSWER):
            error_message = "Illegal state, expected the question ID in the context, but it does not exist"
            logger.error(error_message)
            raise ValueError(error_message)
        question_id = context.get_static_state(self.CONTEXT_QUESTION_TO_ANSWER)
        actioneer_id = context.get_static_state(self.CONTEXT_WENET_USER_ID)
        try:
            transaction = TaskTransaction(None, question_id, self.LABEL_NOT_ANSWER_TRANSACTION,
                                          int(datetime.now().timestamp()), int(datetime.now().timestamp()),
                                          actioneer_id, {}, [])
            service_api.create_task_transaction(transaction)
            message = self._translator.get_translation_instance(user_locale).with_text("not_answer_response").translate()
            response.with_message(TextualResponse(message))
        except TaskTransactionCreationError as e:
            response.with_message(TextualResponse("I'm sorry, something went wrong, try again later"))
            logger.error(
                "Error in the creation of the transaction for not answering the task [%s]. The service API resonded with code %d and message %s"
                % (question_id, e.http_status, json.dumps(e.json_response)))
        finally:
            context.delete_static_state(self.CONTEXT_QUESTION_TO_ANSWER)
            context.delete_static_state(self.CONTEXT_CURRENT_STATE)
            context = self._save_updated_token(context, service_api.client)
            response.with_context(context)
        return response

    def action_answer_remind_later(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        # TODO add a job to remind later
        response = OutgoingEvent(social_details=incoming_event.social_details)
        user_locale = self._get_user_locale(incoming_event)
        context = incoming_event.context
        message = self._translator.get_translation_instance(user_locale).with_text("answer_remind_later_message").translate()
        response.with_message(TextualResponse(message))
        context.delete_static_state(self.CONTEXT_QUESTION_TO_ANSWER)
        context.delete_static_state(self.CONTEXT_CURRENT_STATE)
        response.with_context(context)
        return response

    def action_report_message(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        """
        First step of reporting a single message (either a question or an answer).
        The decision of what to report is taken by the context:
        - intent == self.INTENT_QUESTION_REPORT: we are reporting a question, and the question is already in the context
        - intent == self.INTENT_ANSWER_REPORT: we are reporting an answer
        """
        response = OutgoingEvent(social_details=incoming_event.social_details)
        user_locale = self._get_user_locale(incoming_event)
        context = incoming_event.context
        if intent == self.INTENT_QUESTION_REPORT:
            if not context.has_static_state(self.CONTEXT_QUESTION_TO_ANSWER):
                error_message = "Illegal state, expected the question ID in the context, but it does not exist"
                logger.error(error_message)
                raise ValueError(error_message)
            question_id = context.get_static_state(self.CONTEXT_QUESTION_TO_ANSWER)
            is_question = True
            context.delete_static_state(self.CONTEXT_QUESTION_TO_ANSWER)
        elif intent == self.INTENT_ANSWER_REPORT:
            if not context.has_static_state(self.CONTEXT_ORIGINAL_QUESTION_REPORTING):
                error_message = "Illegal state, expected the question ID in the context, but it does not exist"
                logger.error(error_message)
                raise ValueError(error_message)
            if not context.has_static_state(self.CONTEXT_MESSAGE_TO_REPORT):
                error_message = "Illegal state, expected the transaction ID in the context, but it does not exist"
                logger.error(error_message)
                raise ValueError(error_message)
            question_id = context.get_static_state(self.CONTEXT_MESSAGE_TO_REPORT)
            is_question = False
            context.delete_static_state(self.CONTEXT_MESSAGE_TO_REPORT)
        else:
            error_message = f"Illegal state, received unexpected intent [{intent}] in reporting a message"
            logger.error(error_message)
            raise ValueError(error_message)
        context.with_static_state(self.CONTEXT_MESSAGE_TO_REPORT, question_id)
        context.with_static_state(self.CONTEXT_REPORTING_IS_QUESTION, is_question)
        context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_REPORT_1)
        response.with_context(context)
        message_text = self._translator.get_translation_instance(user_locale).with_text("why_reporting_message").translate()
        button_why_reporting_1_text = self._translator.get_translation_instance(user_locale).with_text("button_why_reporting_1_text").translate()
        button_why_reporting_2_text = self._translator.get_translation_instance(user_locale).with_text("button_why_reporting_2_text").translate()
        button_why_reporting_3_text = self._translator.get_translation_instance(user_locale).with_text("button_why_reporting_3_text").translate()
        message = TelegramRapidAnswerResponse(TextualResponse(message_text), row_displacement=[1, 1, 1])
        message.with_textual_option(button_why_reporting_1_text, self.INTENT_REPORT_ABUSIVE)
        message.with_textual_option(button_why_reporting_2_text, self.INTENT_REPORT_SPAM)
        message.with_textual_option(button_why_reporting_3_text, self.INTENT_CANCEL)
        response.with_message(message)
        return response

    def action_report_message_1(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        """
        Second step of reporting a single message (either a question or an answer).
        We collect the reason of the reporting, and we ask for some more details
        """
        response = OutgoingEvent(social_details=incoming_event.social_details)
        user_locale = self._get_user_locale(incoming_event)
        context = incoming_event.context
        context.with_static_state(self.CONTEXT_REPORTING_REASON, intent)
        context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_REPORT_2)
        message = self._translator.get_translation_instance(user_locale).with_text("report_comment_text").translate()
        response.with_message(TextualResponse(message))
        return response

    def action_report_message_2(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        Final step of reporting a message. The comment of the user is saved and a transaction is sent
        """
        response = OutgoingEvent(social_details=incoming_event.social_details)
        user_locale = self._get_user_locale(incoming_event)
        if isinstance(incoming_event.incoming_message, IncomingTextMessage):
            context = incoming_event.context
            if context is not None:
                service_api = self._get_service_api_interface_connector_from_context(incoming_event.context)
            else:
                raise Exception(f"Missing conversation context for event {incoming_event}")
            if not context.has_static_state(self.CONTEXT_MESSAGE_TO_REPORT):
                error_message = "Illegal state, expected the question to report in the context, but it does not exist"
                logger.error(error_message)
                raise ValueError(error_message)
            if not context.has_static_state(self.CONTEXT_REPORTING_IS_QUESTION):
                error_message = "Illegal state, expected whether the message to report is a question in the context, but it does not exist"
                logger.error(error_message)
                raise ValueError(error_message)
            if not context.has_static_state(self.CONTEXT_REPORTING_REASON):
                error_message = "Illegal state, expected the reporting reason in the context, but it does not exist"
                logger.error(error_message)
                raise ValueError(error_message)
            message_to_report = context.get_static_state(self.CONTEXT_MESSAGE_TO_REPORT)
            is_question = bool(context.get_static_state(self.CONTEXT_REPORTING_IS_QUESTION))
            reporting_reason = context.get_static_state(self.CONTEXT_REPORTING_REASON)
            attributes = {
                "reason": reporting_reason,
                "comment": message_to_report,
            }
            if is_question:
                transaction_label = self.LABEL_REPORT_QUESTION_TRANSACTION
            else:
                transaction_label = self.LABEL_REPORT_ANSWER_TRANSACTION
                attributes.update({"transactionId": message_to_report})
                message_to_report = context.get_static_state(self.CONTEXT_ORIGINAL_QUESTION_REPORTING)
                context.delete_static_state(self.CONTEXT_ORIGINAL_QUESTION_REPORTING)
            actioneer_id = context.get_static_state(self.CONTEXT_WENET_USER_ID)
            try:
                transaction = TaskTransaction(None, message_to_report, transaction_label,
                                              int(datetime.now().timestamp()), int(datetime.now().timestamp()),
                                              actioneer_id, attributes, [])
                service_api.create_task_transaction(transaction)
                logger.info("Sent task transaction: %s" % str(transaction.to_repr()))
                message = self._translator.get_translation_instance(user_locale).with_text(
                    "report_final_message").translate()
                response.with_message(TextualResponse(message))
            except TaskTransactionCreationError as e:
                response.with_message(TextualResponse("I'm sorry, something went wrong, try again later"))
                logger.error(
                    "Error in the creation of the transaction for reporting the task [%s]. The service API resonded with code %d and message %s"
                    % (message_to_report, e.http_status, json.dumps(e.json_response)))
            finally:
                context.delete_static_state(self.CONTEXT_MESSAGE_TO_REPORT)
                context.delete_static_state(self.CONTEXT_REPORTING_IS_QUESTION)
                context.delete_static_state(self.CONTEXT_REPORTING_REASON)
                context.delete_static_state(self.CONTEXT_CURRENT_STATE)
                context = self._save_updated_token(context, service_api.client)
                response.with_context(context)
        else:
            error_message = self._translator.get_translation_instance(user_locale).with_text(
                "answerer_is_not_text").translate()
            response.with_message(TextualResponse(error_message))
        return response

    def action_more_answers(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        response = OutgoingEvent(social_details=incoming_event.social_details)
        user_locale = self._get_user_locale(incoming_event)
        context = incoming_event.context
        if context is not None:
            service_api = self._get_service_api_interface_connector_from_context(incoming_event.context)
        else:
            raise Exception(f"Missing conversation context for event {incoming_event}")
        task_id = context.get_static_state(self.CONTEXT_ORIGINAL_QUESTION_REPORTING)
        actioneer_id = context.get_static_state(self.CONTEXT_WENET_USER_ID)
        try:
            transaction = TaskTransaction(None, task_id, self.LABEL_MORE_ANSWER_TRANSACTION,
                                          int(datetime.now().timestamp()), int(datetime.now().timestamp()),
                                          actioneer_id, {}, [])
            service_api.create_task_transaction(transaction)
            logger.info("Sent task transaction: %s" % str(transaction.to_repr()))
            message = self._translator.get_translation_instance(user_locale).with_text("ask_more_answers_text").translate()
            response.with_message(TextualResponse(message))
        except TaskTransactionCreationError as e:
            response.with_message(TextualResponse("I'm sorry, something went wrong, try again later"))
            logger.error(
                "Error in the creation of the transaction to ask more responses for the task [%s]. The service API resonded with code %d and message %s"
                % (task_id, e.http_status, json.dumps(e.json_response)))
        finally:
            context.delete_static_state(self.CONTEXT_ORIGINAL_QUESTION_REPORTING)
            context.delete_static_state(self.CONTEXT_CURRENT_STATE)
            context.delete_static_state(self.CONTEXT_MESSAGE_TO_REPORT)
            response.with_context(context)
        return response

    def action_answer(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        response = OutgoingEvent(social_details=incoming_event.social_details)
        user_locale = self._get_user_locale(incoming_event)
        context = incoming_event.context
        if context is not None:
            service_api = self._get_service_api_interface_connector_from_context(incoming_event.context)
        else:
            raise Exception(f"Missing conversation context for event {incoming_event}")
        tasks = service_api.get_tasks(self.app_id, has_close_ts=False, limit=3)
        context = self._save_updated_token(context, service_api.client)
        if not tasks:
            response.with_message(TextualResponse(
                self._translator.get_translation_instance(user_locale).with_text("answers_no_tasks").translate()))
        else:
            context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_ANSWERING)
            response.with_message(TextualResponse(
                self._translator.get_translation_instance(user_locale).with_text("answers_tasks_intro").translate()))
            # TODO put the array to empty
            proposed_tasks = ["task1", "task3"]
            for task in tasks:
                questioning_user = service_api.get_user_profile(str(task.requester_id))
                context = self._save_updated_token(context, service_api.client)
                if questioning_user:
                    response.with_message(TextualResponse(f"#{1 + len(proposed_tasks)}: {task.goal.name} - {questioning_user.name.first}"))
                    proposed_tasks.append(task.task_id)
            context.with_static_state(self.CONTEXT_PROPOSED_TASKS, proposed_tasks)
            rapid_answer = RapidAnswerResponse(TextualResponse(self._translator.get_translation_instance(user_locale).with_text("answers_tasks_choose").translate()))
            for i in range(len(proposed_tasks)):
                rapid_answer.with_textual_option(f"#{1 + i}", self.INTENT_ANSWER_PICKED_QUESTION.format(i))
            response.with_message(rapid_answer)
        response.with_context(context)
        return response

