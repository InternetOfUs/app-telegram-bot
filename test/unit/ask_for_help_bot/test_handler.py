from datetime import datetime
from typing import List
from unittest import TestCase
from unittest.mock import Mock

from chatbot_core.model.context import ConversationContext
from chatbot_core.model.details import TelegramDetails
from chatbot_core.model.event import IncomingTelegramEvent
from chatbot_core.model.message import IncomingTextMessage, IncomingCommand
from chatbot_core.translator.translator import TranslatorInstance
from chatbot_core.v3.model.messages import TelegramRapidAnswerResponse, TextualResponse
from chatbot_core.v3.model.outgoing_event import OutgoingEvent
from wenet.interface.client import Oauth2Client
from wenet.interface.service_api import ServiceApiInterface
from wenet.model.callback_message.message import QuestionToAnswerMessage, AnsweredQuestionMessage, AnsweredPickedMessage
from wenet.model.task.task import Task, TaskGoal
from wenet.model.task.transaction import TaskTransaction
from wenet.model.user.profile import WeNetUserProfile

from common.button_payload import ButtonPayload
from common.callback_messages import QuestionExpirationMessage
from test.unit.ask_for_help_bot.mock import MockAskForHelpHandler


class TestAskForHelpHandler(TestCase):

    def test_handle_nearby_question_sensitive_anonymous(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        questioning_user = WeNetUserProfile.empty("questioning_user")
        questioning_user.name.first = "name"
        handler.cache._cache = {}

        response = handler._handle_nearby_question(QuestionToAnswerMessage(
            "app_id",
            "receiver_id",
            {
                "taskId": "task_id",
                "userId": "questioning_user",
                "question": "question",
                "sensitive": True,
                "anonymous": True,
                "positionOfAnswerer": handler.INTENT_ASK_TO_NEARBY
            },
            "question",
            "user_id"), user_object=WeNetUserProfile.empty("receiver_id"), questioning_user=questioning_user)
        self.assertIsInstance(response, TelegramRapidAnswerResponse)
        self.assertEqual(3, len(response.options))
        self.assertEqual(3, len(handler.cache._cache))
        for key in handler.cache._cache:
            cached_item = handler.cache.get(key)
            self.assertEqual("task_id", cached_item["payload"]["task_id"])
            self.assertEqual("question", cached_item["payload"]["question"])
            self.assertEqual(True, cached_item["payload"]["sensitive"])

    def test_handle_nearby_question_sensitive(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        questioning_user = WeNetUserProfile.empty("questioning_user")
        questioning_user.name.first = "name"
        handler.cache._cache = {}

        response = handler._handle_nearby_question(QuestionToAnswerMessage(
            "app_id",
            "receiver_id",
            {
                "taskId": "task_id",
                "userId": "questioning_user",
                "question": "question",
                "sensitive": True,
                "anonymous": False,
                "positionOfAnswerer": handler.INTENT_ASK_TO_NEARBY
            },
            "question",
            "user_id"), user_object=WeNetUserProfile.empty("receiver_id"), questioning_user=questioning_user)
        self.assertIsInstance(response, TelegramRapidAnswerResponse)
        self.assertEqual(3, len(response.options))
        self.assertEqual(3, len(handler.cache._cache))
        for key in handler.cache._cache:
            cached_item = handler.cache.get(key)
            self.assertEqual("task_id", cached_item["payload"]["task_id"])
            self.assertEqual("question", cached_item["payload"]["question"])
            self.assertEqual(True, cached_item["payload"]["sensitive"])
            self.assertEqual("name", cached_item["payload"]["username"])

    def test_handle_nearby_question(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        questioning_user = WeNetUserProfile.empty("questioning_user")
        questioning_user.name.first = "name"
        handler.cache._cache = {}

        response = handler._handle_nearby_question(QuestionToAnswerMessage(
            "app_id",
            "receiver_id",
            {
                "taskId": "task_id",
                "userId": "questioning_user",
                "question": "question",
                "sensitive": False,
                "anonymous": False,
                "positionOfAnswerer": handler.INTENT_ASK_TO_NEARBY
            },
            "question",
            "user_id"), user_object=WeNetUserProfile.empty("receiver_id"), questioning_user=questioning_user)
        self.assertIsInstance(response, TelegramRapidAnswerResponse)
        self.assertEqual(3, len(response.options))
        self.assertEqual(3, len(handler.cache._cache))
        for key in handler.cache._cache:
            cached_item = handler.cache.get(key)
            self.assertEqual("task_id", cached_item["payload"]["task_id"])
            self.assertEqual("question", cached_item["payload"]["question"])
            self.assertEqual(False, cached_item["payload"]["sensitive"])
            self.assertEqual("name", cached_item["payload"]["username"])

    def test_handle_question_sensitive_anonymous(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        questioning_user = WeNetUserProfile.empty("questioning_user")
        questioning_user.name.first = "name"
        handler.cache._cache = {}

        response = handler._handle_question(QuestionToAnswerMessage(
            "app_id",
            "receiver_id",
            {
                "taskId": "task_id",
                "userId": "questioning_user",
                "question": "question",
                "sensitive": True,
                "anonymous": True,
                "positionOfAnswerer": handler.INTENT_ASK_TO_ANYWHERE
            },
            "question",
            "user_id"), user_object=WeNetUserProfile.empty("receiver_id"), questioning_user=questioning_user)
        self.assertIsInstance(response, TelegramRapidAnswerResponse)
        self.assertEqual(4, len(response.options))
        self.assertEqual(4, len(handler.cache._cache))
        for key in handler.cache._cache:
            cached_item = handler.cache.get(key)
            self.assertEqual("task_id", cached_item["payload"]["task_id"])
            self.assertEqual("question", cached_item["payload"]["question"])
            self.assertEqual(True, cached_item["payload"]["sensitive"])

    def test_handle_question_sensitive(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        questioning_user = WeNetUserProfile.empty("questioning_user")
        questioning_user.name.first = "name"
        handler.cache._cache = {}

        response = handler._handle_question(QuestionToAnswerMessage(
            "app_id",
            "receiver_id",
            {
                "taskId": "task_id",
                "userId": "questioning_user",
                "question": "question",
                "sensitive": True,
                "anonymous": False,
                "positionOfAnswerer": handler.INTENT_ASK_TO_ANYWHERE
            },
            "question",
            "user_id"), user_object=WeNetUserProfile.empty("receiver_id"), questioning_user=questioning_user)
        self.assertIsInstance(response, TelegramRapidAnswerResponse)
        self.assertEqual(4, len(response.options))
        self.assertEqual(4, len(handler.cache._cache))
        for key in handler.cache._cache:
            cached_item = handler.cache.get(key)
            self.assertEqual("task_id", cached_item["payload"]["task_id"])
            self.assertEqual("question", cached_item["payload"]["question"])
            self.assertEqual(True, cached_item["payload"]["sensitive"])
            self.assertEqual("name", cached_item["payload"]["username"])

    def test_handle_question(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        questioning_user = WeNetUserProfile.empty("questioning_user")
        questioning_user.name.first = "name"
        handler.cache._cache = {}

        response = handler._handle_question(QuestionToAnswerMessage(
            "app_id",
            "receiver_id",
            {
                "taskId": "task_id",
                "userId": "questioning_user",
                "question": "question",
                "sensitive": False,
                "anonymous": False,
                "positionOfAnswerer": handler.INTENT_ASK_TO_ANYWHERE
            },
            "question",
            "user_id"), user_object=WeNetUserProfile.empty("receiver_id"), questioning_user=questioning_user)
        self.assertIsInstance(response, TelegramRapidAnswerResponse)
        self.assertEqual(4, len(response.options))
        self.assertEqual(4, len(handler.cache._cache))
        for key in handler.cache._cache:
            cached_item = handler.cache.get(key)
            self.assertEqual("task_id", cached_item["payload"]["task_id"])
            self.assertEqual("question", cached_item["payload"]["question"])
            self.assertEqual(False, cached_item["payload"]["sensitive"])
            self.assertEqual("name", cached_item["payload"]["username"])

    def test_handle_answered_question_sensitive_anonymous(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        answerer_user = WeNetUserProfile.empty("answerer_user")
        answerer_user.name.first = "name"
        handler.cache._cache = {}

        response = handler._handle_answered_question(AnsweredQuestionMessage(
            "app_id",
            "receiver_id",
            "answer",
            "transaction_id",
            "user_id",
            {
                "taskId": "task_id",
                "userId": "questioning_user",
                "question": "question",
                "transactionId": "transaction_id",
                "answer": "answer",
                "anonymous": True
            }), user_object=WeNetUserProfile.empty("questioning_user"), answerer_user=answerer_user)
        self.assertIsInstance(response, TelegramRapidAnswerResponse)
        self.assertEqual(2, len(response.options))
        self.assertEqual(2, len(handler.cache._cache))
        for key in handler.cache._cache:
            cached_item = handler.cache.get(key)
            self.assertEqual("transaction_id", cached_item["payload"]["transaction_id"])
            self.assertEqual("task_id", cached_item["payload"]["task_id"])

    def test_handle_answered_question(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        answerer_user = WeNetUserProfile.empty("answerer_user")
        answerer_user.name.first = "name"
        handler.cache._cache = {}

        response = handler._handle_answered_question(AnsweredQuestionMessage(
            "app_id",
            "receiver_id",
            "answer",
            "transaction_id",
            "user_id",
            {
                "taskId": "task_id",
                "userId": "questioning_user",
                "question": "question",
                "transactionId": "transaction_id",
                "answer": "answer",
                "anonymous": False
            }), user_object=WeNetUserProfile.empty("questioning_user"), answerer_user=answerer_user)
        self.assertIsInstance(response, TelegramRapidAnswerResponse)
        self.assertEqual(2, len(response.options))
        self.assertEqual(2, len(handler.cache._cache))
        for key in handler.cache._cache:
            cached_item = handler.cache.get(key)
            self.assertEqual("transaction_id", cached_item["payload"]["transaction_id"])
            self.assertEqual("task_id", cached_item["payload"]["task_id"])

    def test_handle_answered_picked(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        answerer_user = WeNetUserProfile.empty("answerer_user")
        answerer_user.name.first = "name"
        handler.cache._cache = {}

        response = handler._handle_answered_picked(AnsweredPickedMessage(
            "app_id",
            "receiver_id",
            "task_id",
            "transaction_id",
            {
                "taskId": "task_id",
                "question": "question",
                "transactionId": "transaction_id"
            }), user_object=WeNetUserProfile.empty("questioning_user"))
        self.assertIsInstance(response, TextualResponse)

    def test_handle_question_expiration(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")
        service_api = ServiceApiInterface(Oauth2Client("app_id", "app_secret", "id", handler.oauth_cache, token_endpoint_url=""), "")
        service_api.get_task = Mock(return_value=Task("task_id", None, None, "task_type_id", "questioning_user", "app_id", None, TaskGoal("question", ""), attributes={
            "domain": handler.INTENT_STUDYING_CAREER,
            "domainInterest": handler.INTENT_DIFFERENT_DOMAIN,
            "beliefsAndValues": handler.INTENT_DIFFERENT_BELIEF_VALUES,
            "sensitive": False,
            "anonymous": False,
            "socialCloseness": handler.INTENT_SIMILAR_SOCIALLY,
            "positionOfAnswerer": handler.INTENT_ASK_TO_NEARBY,
            "maxUsers": 10,
            "maxAnswers": 15,
            "expirationDate": 1652884728
        }, transactions=[
            TaskTransaction(
                transaction_id="transaction_id",
                task_id="task_id_1",
                label=handler.LABEL_ANSWER_TRANSACTION,
                creation_ts=int(datetime.now().timestamp()),
                last_update_ts=int(datetime.now().timestamp()),
                actioneer_id="answerer_user",
                attributes={"answer": "answer", "anonymous": True}
            ),
            TaskTransaction(
                transaction_id="transaction_id",
                task_id="task_id_2",
                label=handler.LABEL_ANSWER_TRANSACTION,
                creation_ts=int(datetime.now().timestamp()),
                last_update_ts=int(datetime.now().timestamp()),
                actioneer_id="answerer_user",
                attributes={"answer": "answer", "anonymous": True}
            )
        ]))
        handler._get_service_api_interface_connector_from_context = Mock(return_value=service_api)
        handler.send_notification = Mock()
        service_api.get_user_profile = Mock(return_value=WeNetUserProfile.empty("answerer_user"))
        questioner_user = WeNetUserProfile.empty("answerer_user")
        questioner_user.name.first = "name"

        handler.cache._cache = {}

        response = handler._handle_question_expiration(
            message=QuestionExpirationMessage(
                app_id="app_id",
                receiver_id="receiver_id",
                task_id="task_id",
                question="question",
                transaction_ids=["0", "1"],
                attributes={
                    "taskId": "task_id",
                    "userId": "user_id",
                    "question": "test_question",
                    "listOfTransactionIds": ["0", "1"],
                    "answer": "test_answer",
                    "anonymous": False
                }),
            service_api=service_api,
            user_object=questioner_user
        )
        self.assertIsInstance(response, List)
        self.assertEqual(1, len(response))
        self.assertIsInstance(response[0], TelegramRapidAnswerResponse)
        self.assertEqual(1, len(handler.cache._cache))

    def test_action_question(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")

        response = handler.action_question_0(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", handler.INTENT_ASK, ""), ConversationContext()), handler.INTENT_ASK)
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(1, len(response.messages))
        self.assertIsInstance(response.messages[0], TextualResponse)
        self.assertTrue(handler.CONTEXT_CURRENT_STATE in response.context._static_context and response.context._static_context[handler.CONTEXT_CURRENT_STATE] == handler.STATE_QUESTION_0)

    def test_action_question_1(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")

        response = handler.action_question_1(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingTextMessage("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", "text"), ConversationContext()), "")
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(1, len(response.messages))
        self.assertIsInstance(response.messages[0], TelegramRapidAnswerResponse)
        self.assertEqual(11, len(response.messages[0].options))
        self.assertTrue(handler.CONTEXT_CURRENT_STATE in response.context._static_context and response.context._static_context[handler.CONTEXT_CURRENT_STATE] == handler.STATE_QUESTION_1)

    def test_action_question_2(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")

        response = handler.action_question_2(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", handler.INTENT_STUDYING_CAREER, ""), ConversationContext()), handler.INTENT_STUDYING_CAREER)
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(1, len(response.messages))
        self.assertIsInstance(response.messages[0], TelegramRapidAnswerResponse)
        self.assertEqual(3, len(response.messages[0].options))
        self.assertTrue(handler.CONTEXT_CURRENT_STATE in response.context._static_context and response.context._static_context[handler.CONTEXT_CURRENT_STATE] == handler.STATE_QUESTION_2)

    def test_action_question_3(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")

        response = handler.action_question_3(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", handler.INTENT_DIFFERENT_DOMAIN, ""), ConversationContext()), handler.INTENT_DIFFERENT_DOMAIN)
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(1, len(response.messages))
        self.assertIsInstance(response.messages[0], TelegramRapidAnswerResponse)
        self.assertEqual(3, len(response.messages[0].options))
        self.assertTrue(handler.CONTEXT_CURRENT_STATE in response.context._static_context and response.context._static_context[handler.CONTEXT_CURRENT_STATE] == handler.STATE_QUESTION_3)

    def test_action_question_4(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")

        response = handler.action_question_4(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", handler.INTENT_DIFFERENT_BELIEF_VALUES, ""), ConversationContext()), handler.INTENT_DIFFERENT_BELIEF_VALUES)
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(1, len(response.messages))
        self.assertIsInstance(response.messages[0], TelegramRapidAnswerResponse)
        self.assertEqual(2, len(response.messages[0].options))
        self.assertTrue(handler.CONTEXT_CURRENT_STATE in response.context._static_context and response.context._static_context[handler.CONTEXT_CURRENT_STATE] == handler.STATE_QUESTION_4)

    def test_action_question_4_1(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")

        response = handler.action_question_4_1(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", handler.INTENT_SENSITIVE_QUESTION, ""), ConversationContext()), handler.INTENT_SENSITIVE_QUESTION)
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(1, len(response.messages))
        self.assertIsInstance(response.messages[0], TelegramRapidAnswerResponse)
        self.assertEqual(2, len(response.messages[0].options))
        self.assertTrue(handler.CONTEXT_CURRENT_STATE in response.context._static_context and response.context._static_context[handler.CONTEXT_CURRENT_STATE] == handler.STATE_QUESTION_4_1)

    def test_action_question_5(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")

        response = handler.action_question_5(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", handler.INTENT_ANONYMOUS_QUESTION, ""), ConversationContext()), handler.INTENT_ANONYMOUS_QUESTION)
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(1, len(response.messages))
        self.assertIsInstance(response.messages[0], TelegramRapidAnswerResponse)
        self.assertEqual(3, len(response.messages[0].options))
        self.assertTrue(handler.CONTEXT_CURRENT_STATE in response.context._static_context and response.context._static_context[handler.CONTEXT_CURRENT_STATE] == handler.STATE_QUESTION_5)

    def test_action_question_6(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")

        response = handler.action_question_6(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", handler.INTENT_SIMILAR_SOCIALLY, ""), ConversationContext()), handler.INTENT_SIMILAR_SOCIALLY)
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(1, len(response.messages))
        self.assertIsInstance(response.messages[0], TelegramRapidAnswerResponse)
        self.assertEqual(2, len(response.messages[0].options))
        self.assertTrue(handler.CONTEXT_CURRENT_STATE in response.context._static_context and response.context._static_context[handler.CONTEXT_CURRENT_STATE] == handler.STATE_QUESTION_6)

    def test_action_question_final(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")
        service_api = ServiceApiInterface(Oauth2Client("app_id", "app_secret", "id", handler.oauth_cache, token_endpoint_url=""), "")
        service_api.create_task = Mock()
        handler._get_service_api_interface_connector_from_context = Mock(return_value=service_api)

        response = handler.action_question_final(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", handler.INTENT_ASK_TO_NEARBY, ""), ConversationContext(static_context={
            handler.CONTEXT_WENET_USER_ID: "",
            handler.CONTEXT_ASKED_QUESTION: "question",
            handler.CONTEXT_QUESTION_DOMAIN: handler.INTENT_STUDYING_CAREER,
            handler.CONTEXT_DOMAIN_INTEREST: handler.INTENT_DIFFERENT_DOMAIN,
            handler.CONTEXT_BELIEF_VALUES_SIMILARITY: handler.INTENT_DIFFERENT_BELIEF_VALUES,
            handler.CONTEXT_SOCIAL_CLOSENESS: handler.INTENT_SIMILAR_SOCIALLY,
            handler.CONTEXT_SENSITIVE_QUESTION: False
        })), handler.INTENT_ASK_TO_NEARBY)
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(1, len(response.messages))
        self.assertIsInstance(response.messages[0], TextualResponse)

    def test_action_answer_question_sensitive(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")

        response = handler.action_answer_question(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", handler.INTENT_ANSWER_QUESTION, ""), ConversationContext(static_context={
            handler.CONTEXT_WENET_USER_ID: ""
        })), ButtonPayload({
            "task_id": "task_id",
            "question": "question",
            "sensitive": True,
            "username": "username",
            "related_buttons": ["button_ids"],
        }, handler.INTENT_ANSWER_QUESTION))
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(2, len(response.messages))
        self.assertIsInstance(response.messages[0], TextualResponse)
        self.assertIsInstance(response.messages[1], TextualResponse)
        self.assertTrue(handler.CONTEXT_CURRENT_STATE in response.context._static_context and response.context._static_context[handler.CONTEXT_CURRENT_STATE] == handler.STATE_ANSWERING_SENSITIVE)

    def test_action_answer_question(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")

        response = handler.action_answer_question(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", handler.INTENT_ANSWER_QUESTION, ""), ConversationContext(static_context={
            handler.CONTEXT_WENET_USER_ID: ""
        })), ButtonPayload({
            "task_id": "task_id",
            "question": "question",
            "sensitive": False,
            "username": "username",
            "related_buttons": ["button_ids"],
        }, handler.INTENT_ANSWER_QUESTION))
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(2, len(response.messages))
        self.assertIsInstance(response.messages[0], TextualResponse)
        self.assertIsInstance(response.messages[1], TextualResponse)
        self.assertTrue(handler.CONTEXT_CURRENT_STATE in response.context._static_context and response.context._static_context[handler.CONTEXT_CURRENT_STATE] == handler.STATE_ANSWERING)

    def test_action_answer_picked_question_sensitive(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")
        service_api = ServiceApiInterface(Oauth2Client("app_id", "app_secret", "id", handler.oauth_cache, token_endpoint_url=""), "")
        service_api.get_task = Mock(return_value=Task("task_id", None, None, "task_type_id", "questioning_user", "app_id", None, TaskGoal("question", ""), attributes={
            "domain": handler.INTENT_STUDYING_CAREER,
            "domainInterest": handler.INTENT_DIFFERENT_DOMAIN,
            "beliefsAndValues": handler.INTENT_DIFFERENT_BELIEF_VALUES,
            "sensitive": True,
            "anonymous": True,
            "socialCloseness": handler.INTENT_SIMILAR_SOCIALLY,
            "positionOfAnswerer":  handler.INTENT_ASK_TO_NEARBY,
            "maxUsers": 10
        }, transactions=[TaskTransaction("transaction_id", "task_id", handler.LABEL_ANSWER_TRANSACTION, int(datetime.now().timestamp()), int(datetime.now().timestamp()), "answerer_user", {"answer": "answer", "anonymous": True})]))
        handler._get_service_api_interface_connector_from_context = Mock(return_value=service_api)

        response = handler.action_answer_picked_question(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", handler.INTENT_ANSWER_QUESTION, ""), ConversationContext(static_context={
            handler.CONTEXT_WENET_USER_ID: ""
        })), ButtonPayload({
            "task_id": "task_id",
            "question": "question",
            "sensitive": True,
            "username": "username",
            "related_buttons": ["button_ids"],
        }, handler.INTENT_ANSWER_QUESTION))
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(2, len(response.messages))
        self.assertIsInstance(response.messages[0], TextualResponse)
        self.assertIsInstance(response.messages[1], TextualResponse)
        self.assertTrue(handler.CONTEXT_CURRENT_STATE in response.context._static_context and response.context._static_context[handler.CONTEXT_CURRENT_STATE] == handler.STATE_ANSWERING_SENSITIVE)
        self.assertTrue(handler.CONTEXT_QUESTION_TO_ANSWER in response.context._static_context and response.context._static_context[handler.CONTEXT_QUESTION_TO_ANSWER] == "task_id")

    def test_action_answer_picked_question(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")
        service_api = ServiceApiInterface(Oauth2Client("app_id", "app_secret", "id", handler.oauth_cache, token_endpoint_url=""), "")
        service_api.get_task = Mock(return_value=Task("task_id", None, None, "task_type_id", "questioning_user", "app_id", None, TaskGoal("question", ""), attributes={
            "domain": handler.INTENT_STUDYING_CAREER,
            "domainInterest": handler.INTENT_DIFFERENT_DOMAIN,
            "beliefsAndValues": handler.INTENT_DIFFERENT_BELIEF_VALUES,
            "sensitive": False,
            "anonymous": False,
            "socialCloseness": handler.INTENT_SIMILAR_SOCIALLY,
            "positionOfAnswerer":  handler.INTENT_ASK_TO_NEARBY,
            "maxUsers": 10
        }, transactions=[TaskTransaction("transaction_id", "task_id", handler.LABEL_ANSWER_TRANSACTION, int(datetime.now().timestamp()), int(datetime.now().timestamp()), "answerer_user", {"answer": "answer", "anonymous": True})]))
        handler._get_service_api_interface_connector_from_context = Mock(return_value=service_api)

        response = handler.action_answer_picked_question(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", handler.INTENT_ANSWER_QUESTION, ""), ConversationContext(static_context={
            handler.CONTEXT_WENET_USER_ID: ""
        })), ButtonPayload({
            "task_id": "task_id",
            "question": "question",
            "sensitive": False,
            "username": "username",
            "related_buttons": ["button_ids"],
        }, handler.INTENT_ANSWER_QUESTION))
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(2, len(response.messages))
        self.assertIsInstance(response.messages[0], TextualResponse)
        self.assertIsInstance(response.messages[1], TextualResponse)
        self.assertTrue(handler.CONTEXT_CURRENT_STATE in response.context._static_context and response.context._static_context[handler.CONTEXT_CURRENT_STATE] == handler.STATE_ANSWERING)
        self.assertTrue(handler.CONTEXT_QUESTION_TO_ANSWER in response.context._static_context and response.context._static_context[handler.CONTEXT_QUESTION_TO_ANSWER] == "task_id")

    def test_action_answer_sensitive_question(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")

        response = handler.action_answer_sensitive_question(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingTextMessage("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", "text"), ConversationContext(static_context={
            handler.CONTEXT_QUESTION_TO_ANSWER: "task_id"
        })), "")
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(1, len(response.messages))
        self.assertIsInstance(response.messages[0], TelegramRapidAnswerResponse)
        self.assertEqual(2, len(response.messages[0].options))
        self.assertTrue(handler.CONTEXT_CURRENT_STATE in response.context._static_context and response.context._static_context[handler.CONTEXT_CURRENT_STATE] == handler.STATE_ANSWERING_ANONYMOUSLY)

    def test_action_answer_question_anonymously(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")
        service_api = ServiceApiInterface(Oauth2Client("app_id", "app_secret", "id", handler.oauth_cache, token_endpoint_url=""), "")
        service_api.create_task_transaction = Mock()
        handler._get_service_api_interface_connector_from_context = Mock(return_value=service_api)

        response = handler.action_answer_question_anonymously(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", handler.INTENT_ANSWER_ANONYMOUSLY, ""), ConversationContext(static_context={
            handler.CONTEXT_QUESTION_TO_ANSWER: "task_id",
            handler.CONTEXT_ANSWER_TO_QUESTION: "answer",
            handler.CONTEXT_WENET_USER_ID: "user_id"
        })), handler.INTENT_ANSWER_ANONYMOUSLY)
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(2, len(response.messages))
        self.assertIsInstance(response.messages[0], TextualResponse)

    def test_action_answer_question_2(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")
        service_api = ServiceApiInterface(Oauth2Client("app_id", "app_secret", "id", handler.oauth_cache, token_endpoint_url=""), "")
        service_api.create_task_transaction = Mock()
        handler._get_service_api_interface_connector_from_context = Mock(return_value=service_api)

        response = handler.action_answer_question_2(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingTextMessage("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", "answer"), ConversationContext(static_context={
            handler.CONTEXT_QUESTION_TO_ANSWER: "task_id",
            handler.CONTEXT_WENET_USER_ID: "user_id"
        })), "")
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(2, len(response.messages))
        self.assertIsInstance(response.messages[0], TextualResponse)

    def test_action_best_answer_0(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")
        service_api = ServiceApiInterface(Oauth2Client("app_id", "app_secret", "id", handler.oauth_cache, token_endpoint_url=""), "")
        service_api.get_task = Mock(return_value=Task("task_id", None, None, "task_type_id", "questioning_user", "app_id", None, TaskGoal("question", ""), attributes={
            "domain": handler.INTENT_STUDYING_CAREER,
            "domainInterest": handler.INTENT_DIFFERENT_DOMAIN,
            "beliefsAndValues": handler.INTENT_DIFFERENT_BELIEF_VALUES,
            "sensitive": True,
            "anonymous": False,
            "socialCloseness": handler.INTENT_SIMILAR_SOCIALLY,
            "positionOfAnswerer":  handler.INTENT_ASK_TO_NEARBY,
            "maxUsers": 10
        }, transactions=[
            TaskTransaction("transaction_id", "task_id", handler.LABEL_ANSWER_TRANSACTION, int(datetime.now().timestamp()), int(datetime.now().timestamp()), "answerer_user", {"answer": "answer", "anonymous": True})]))
        service_api.get_user_profile = Mock(return_value=WeNetUserProfile.empty("questioning_user"))
        handler._get_service_api_interface_connector_from_context = Mock(return_value=service_api)

        response = handler.action_best_answer_0(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", handler.INTENT_BEST_ANSWER, ""), ConversationContext(static_context={})), ButtonPayload({
            "transaction_id": "transaction_id",
            "task_id": "task_id",
            "related_buttons": ["button_ids"]
        }, handler.INTENT_BEST_ANSWER))
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(1, len(response.messages))
        self.assertIsInstance(response.messages[0], TelegramRapidAnswerResponse)
        self.assertEqual(7, len(response.messages[0].options))
        self.assertTrue(handler.CONTEXT_CURRENT_STATE in response.context._static_context and response.context._static_context[handler.CONTEXT_CURRENT_STATE] == handler.STATE_BEST_ANSWER_PUBLISH)

    def test_action_best_answer_0_no_channel_id(self):
        handler = MockAskForHelpHandler()
        handler.channel_id = None
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")
        service_api = ServiceApiInterface(Oauth2Client("app_id", "app_secret", "id", handler.oauth_cache, token_endpoint_url=""), "")
        service_api.get_task = Mock(return_value=Task("task_id", None, None, "task_type_id", "questioning_user", "app_id", None, TaskGoal("question", ""), attributes={
            "domain": handler.INTENT_STUDYING_CAREER,
            "domainInterest": handler.INTENT_DIFFERENT_DOMAIN,
            "beliefsAndValues": handler.INTENT_DIFFERENT_BELIEF_VALUES,
            "sensitive": True,
            "anonymous": False,
            "socialCloseness": handler.INTENT_SIMILAR_SOCIALLY,
            "positionOfAnswerer":  handler.INTENT_ASK_TO_NEARBY,
            "maxUsers": 10
        }, transactions=[TaskTransaction("transaction_id", "task_id", handler.LABEL_ANSWER_TRANSACTION, int(datetime.now().timestamp()), int(datetime.now().timestamp()), "answerer_user", {"answer": "answer", "anonymous": True})]))
        service_api.get_user_profile = Mock(return_value=WeNetUserProfile.empty("questioning_user"))
        handler._get_service_api_interface_connector_from_context = Mock(return_value=service_api)

        response = handler.action_best_answer_0(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", handler.INTENT_BEST_ANSWER, ""), ConversationContext(static_context={})), ButtonPayload({
            "transaction_id": "transaction_id",
            "task_id": "task_id",
            "related_buttons": ["button_ids"]
        }, handler.INTENT_BEST_ANSWER))
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(1, len(response.messages))
        self.assertIsInstance(response.messages[0], TextualResponse)
        self.assertTrue(handler.CONTEXT_CURRENT_STATE in response.context._static_context and response.context._static_context[handler.CONTEXT_CURRENT_STATE] == handler.STATE_BEST_ANSWER_0)

    def test_action_best_answer_publish(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")
        service_api = ServiceApiInterface(Oauth2Client("app_id", "app_secret", "id", handler.oauth_cache, token_endpoint_url=""), "")
        service_api.get_task = Mock(return_value=Task("task_id", None, None, "task_type_id", "questioning_user", "app_id", None, TaskGoal("question", ""), attributes={
            "domain": handler.INTENT_STUDYING_CAREER,
            "domainInterest": handler.INTENT_DIFFERENT_DOMAIN,
            "beliefsAndValues": handler.INTENT_DIFFERENT_BELIEF_VALUES,
            "sensitive": False,
            "anonymous": False,
            "socialCloseness": handler.INTENT_SIMILAR_SOCIALLY,
            "positionOfAnswerer": handler.INTENT_ASK_TO_NEARBY,
            "maxUsers": 10,
            "maxAnswers": 15,
            "expirationDate": 1652705325
        }, transactions=[TaskTransaction(
            transaction_id="transaction_id",
            task_id="task_id",
            label=handler.LABEL_ANSWER_TRANSACTION,
            creation_ts=int(datetime.now().timestamp()),
            last_update_ts=int(datetime.now().timestamp()),
            actioneer_id="answerer_user",
            attributes={"answer": "answer", "anonymous": True}
        )]))
        handler._get_service_api_interface_connector_from_context = Mock(return_value=service_api)
        handler.send_notification = Mock()
        service_api.get_user_profile = Mock(return_value=WeNetUserProfile.empty("answerer_user"))

        response = handler.action_best_answer_publish(
            incoming_event=IncomingTelegramEvent(
                instance_namespace="",
                social_details=TelegramDetails(1, 1, ""),
                incoming_message=IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", handler.INTENT_BEST_ANSWER, ""),
                context=ConversationContext(
                    static_context={
                        handler.CONTEXT_TASK_ID: "task_id",
                        handler.CONTEXT_TRANSACTION_ID: "transaction_id",
                        handler.CONTEXT_QUESTIONER_NAME: "questioner_name",
                        handler.CONTEXT_QUESTION: "question",
                        handler.CONTEXT_BEST_ANSWER: "answer"
                        })
            ),
            intent=handler.INTENT_PUBLISH)
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(1, len(response.messages))
        self.assertIsInstance(response.messages[0], TextualResponse)
        self.assertTrue(handler.CONTEXT_CURRENT_STATE in response.context._static_context and response.context._static_context[handler.CONTEXT_CURRENT_STATE] == handler.STATE_BEST_ANSWER_0)
        handler.send_notification.assert_called()

    def test_action_best_answer_publish_intent_not_publish(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")
        service_api = ServiceApiInterface(Oauth2Client("app_id", "app_secret", "id", handler.oauth_cache, token_endpoint_url=""), "")
        service_api.get_task = Mock(return_value=Task("task_id", None, None, "task_type_id", "questioning_user", "app_id", None, TaskGoal("question", ""), attributes={
            "domain": handler.INTENT_STUDYING_CAREER,
            "domainInterest": handler.INTENT_DIFFERENT_DOMAIN,
            "beliefsAndValues": handler.INTENT_DIFFERENT_BELIEF_VALUES,
            "sensitive": False,
            "anonymous": False,
            "socialCloseness": handler.INTENT_SIMILAR_SOCIALLY,
            "positionOfAnswerer":  handler.INTENT_ASK_TO_NEARBY,
            "maxUsers": 10,
            "maxAnswers": 15,
            "expirationDate": 1652711297
        }, transactions=[TaskTransaction("transaction_id", "task_id", handler.LABEL_ANSWER_TRANSACTION, int(datetime.now().timestamp()), int(datetime.now().timestamp()), "answerer_user", {"answer": "answer", "anonymous": True})]))
        handler._get_service_api_interface_connector_from_context = Mock(return_value=service_api)
        handler.send_notification = Mock()
        service_api.get_user_profile = Mock(return_value=WeNetUserProfile.empty("answerer_user"))
        response = handler.action_best_answer_publish(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", handler.INTENT_BEST_ANSWER, ""), ConversationContext(static_context={
            handler.CONTEXT_TASK_ID: "task_id",
            handler.CONTEXT_TRANSACTION_ID: "transaction_id",
            handler.CONTEXT_QUESTIONER_NAME: "questioner_name",
            handler.CONTEXT_QUESTION: "question",
            handler.CONTEXT_BEST_ANSWER: "answer"
        })), handler.INTENT_NOT_PUBLISH)
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(1, len(response.messages))
        self.assertIsInstance(response.messages[0], TextualResponse)
        self.assertTrue(handler.CONTEXT_CURRENT_STATE in response.context._static_context and response.context._static_context[handler.CONTEXT_CURRENT_STATE] == handler.STATE_BEST_ANSWER_0)
        handler.send_notification.assert_not_called()

    def test_action_best_answer_1(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")

        response = handler.action_best_answer_1(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingTextMessage("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", "reason"), ConversationContext(static_context={})), "")
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(1, len(response.messages))
        self.assertIsInstance(response.messages[0], TelegramRapidAnswerResponse)
        self.assertEqual(5, len(response.messages[0].options))
        self.assertTrue(handler.CONTEXT_CURRENT_STATE in response.context._static_context and response.context._static_context[handler.CONTEXT_CURRENT_STATE] == handler.STATE_BEST_ANSWER_1)

    def test_action_best_answer_2(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")
        service_api = ServiceApiInterface(Oauth2Client("app_id", "app_secret", "id", handler.oauth_cache, token_endpoint_url=""), "")
        service_api.create_task_transaction = Mock()
        handler._get_service_api_interface_connector_from_context = Mock(return_value=service_api)
        service_api.get_task = Mock(return_value=Task("task_id", None, None, "task_type_id", "questioning_user", "app_id", None, TaskGoal("question", ""), attributes={
            "domain": handler.INTENT_STUDYING_CAREER,
            "domainInterest": handler.INTENT_DIFFERENT_DOMAIN,
            "beliefsAndValues": handler.INTENT_DIFFERENT_BELIEF_VALUES,
            "sensitive": False,
            "anonymous": False,
            "socialCloseness": handler.INTENT_SIMILAR_SOCIALLY,
            "positionOfAnswerer": handler.INTENT_ASK_TO_NEARBY,
            "maxUsers": 10,
            "maxAnswers": 15,
            "expirationDate": 1652705325
        }, transactions=[TaskTransaction(
            transaction_id="transaction_id",
            task_id="task_id",
            label=handler.LABEL_ANSWER_TRANSACTION,
            creation_ts=int(datetime.now().timestamp()),
            last_update_ts=int(datetime.now().timestamp()),
            actioneer_id="answerer_user",
            attributes={"answer": "answer", "anonymous": True}
        )]))
        service_api.get_user_profile = Mock(return_value=WeNetUserProfile.empty("questioning_user"))
        response = handler.action_best_answer_2(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", handler.INTENT_EXTREMELY_HELPFUL, ""), ConversationContext(static_context={
            handler.CONTEXT_WENET_USER_ID: "",
            handler.CONTEXT_TRANSACTION_ID: "transaction_id",
            handler.CONTEXT_TASK_ID: "task_id",
            handler.CONTEXT_CHOSEN_ANSWER_REASON: "reason"
        })), handler.INTENT_EXTREMELY_HELPFUL)
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(2, len(response.messages))
        self.assertIsInstance(response.messages[0], TextualResponse)

    def test_action_like_answer(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")
        service_api = ServiceApiInterface(Oauth2Client("app_id", "app_secret", "id", handler.oauth_cache, token_endpoint_url=""), "")
        service_api.create_task_transaction = Mock()
        service_api.get_user_profile = Mock(return_value=WeNetUserProfile.empty("questioning_user"))
        handler._get_service_api_interface_connector_from_context = Mock(return_value=service_api)

        response = handler.action_like_answer(
            IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", handler.INTENT_LIKE_ANSWER, ""), ConversationContext(static_context={
                handler.CONTEXT_WENET_USER_ID: ""
            })),
            ButtonPayload({
                "transaction_id": "transaction_id",
                "task_id": "task_id",
                "related_buttons": ["button_ids"]
                },
            handler.INTENT_LIKE_ANSWER)
        )
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(1, len(response.messages))
        self.assertIsInstance(response.messages[0], TextualResponse)

    def test_get_eligible_tasks(self):
        handler = MockAskForHelpHandler()
        service_api = ServiceApiInterface(Oauth2Client("app_id", "app_secret", "id", handler.oauth_cache, token_endpoint_url=""), "")

        service_api.get_all_tasks = Mock(return_value=[
            Task("task_id-1", None, None, "task_type_id", "questioning_user-1", "app_id", None, TaskGoal("question", ""),
                 attributes={
                    "domain": handler.INTENT_STUDYING_CAREER,
                    "domainInterest": handler.INTENT_DIFFERENT_DOMAIN,
                    "beliefsAndValues": handler.INTENT_DIFFERENT_BELIEF_VALUES,
                    "sensitive": False,
                    "anonymous": False,
                    "socialCloseness": handler.INTENT_SIMILAR_SOCIALLY,
                    "positionOfAnswerer": handler.INTENT_ASK_TO_NEARBY,
                    "maxUsers": 10,
                    "maxAnswers": 15,
                    "expirationDate": 1600000000
                },
            transactions=[
                TaskTransaction(
                    transaction_id="transaction_id-1",
                    task_id="task_id-1",
                    label=handler.LABEL_MORE_ANSWER_TRANSACTION,
                    creation_ts=int(datetime.now().timestamp()),
                    last_update_ts=int(datetime.now().timestamp()),
                    actioneer_id="answerer_user-1",
                    attributes={"expirationDate": 1600000000}
                )]
            ),
            Task("task_id-2", None, None, "task_type_id", "questioning_user-2", "app_id", None, TaskGoal("question", ""),
                 attributes={
                     "domain": handler.INTENT_STUDYING_CAREER,
                     "domainInterest": handler.INTENT_DIFFERENT_DOMAIN,
                     "beliefsAndValues": handler.INTENT_DIFFERENT_BELIEF_VALUES,
                     "sensitive": False,
                     "anonymous": False,
                     "socialCloseness": handler.INTENT_SIMILAR_SOCIALLY,
                     "positionOfAnswerer": handler.INTENT_ASK_TO_NEARBY,
                     "maxUsers": 10,
                     "maxAnswers": 15,
                     "expirationDate": 1600000000
                 },
                 transactions=[
                     TaskTransaction(
                         transaction_id="transaction_id-2",
                         task_id="task_id-2",
                         label=handler.LABEL_MORE_ANSWER_TRANSACTION,
                         creation_ts=int(datetime.now().timestamp()),
                         last_update_ts=int(datetime.now().timestamp()),
                         actioneer_id="answerer_user-2",
                         attributes={"expirationDate": 1600000002}
                     )]
                 )
        ])
        current_date = 1600000001
        response = handler._get_eligible_tasks(service_api=service_api, user_id="user_id", current_date=current_date)

        self.assertIsInstance(response, List)
        self.assertEqual(1, len(response))

    def test_action_badges(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")

        response = handler.action_badges(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", handler.INTENT_BADGES, ""), ConversationContext()), handler.INTENT_BADGES)
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(1, len(response.messages))
        self.assertIsInstance(response.messages[0], TextualResponse)

    def test_action_start(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")

        response = handler.action_start(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", handler.INTENT_START, ""), ConversationContext()), handler.INTENT_START)
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(6, len(response.messages))
        self.assertIsInstance(response.messages[0], TextualResponse)
        self.assertIsInstance(response.messages[1], TextualResponse)
        self.assertIsInstance(response.messages[2], TextualResponse)
        self.assertIsInstance(response.messages[3], TextualResponse)
        self.assertIsInstance(response.messages[4], TextualResponse)
        self.assertIsInstance(response.messages[5], TelegramRapidAnswerResponse)
        self.assertEqual(1, len(response.messages[5].options))
