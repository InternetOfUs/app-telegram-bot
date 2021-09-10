from datetime import datetime
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
from wenet.model.callback_message.message import QuestionToAnswerMessage, AnsweredQuestionMessage
from wenet.model.task.task import Task, TaskGoal
from wenet.model.task.transaction import TaskTransaction
from wenet.model.user.profile import WeNetUserProfile

from common.button_payload import ButtonPayload
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

        response = handler.handle_nearby_question(QuestionToAnswerMessage(
            "app_id",
            "receiver_id",
            {
                "taskId": "task_id",
                "userId": "questioning_user",
                "question": "question"
            },
            "question",
            "user_id"), user_object=WeNetUserProfile.empty("receiver_id"), questioning_user=questioning_user, sensitive=True, anonymous=True)
        self.assertIsInstance(response, TelegramRapidAnswerResponse)
        self.assertEqual(3, len(response.options))
        self.assertEqual(3, len(handler.cache._cache))
        for key in handler.cache._cache:
            cached_item = handler.cache.get(key)
            self.assertEqual("task_id", cached_item["payload"]["task_id"])
            self.assertEqual("question", cached_item["payload"]["question"])
            self.assertEqual(True, cached_item["payload"]["sensitive"])
            self.assertEqual("Anonymous", cached_item["payload"]["username"])

    def test_handle_nearby_question_sensitive(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        questioning_user = WeNetUserProfile.empty("questioning_user")
        questioning_user.name.first = "name"
        handler.cache._cache = {}

        response = handler.handle_nearby_question(QuestionToAnswerMessage(
            "app_id",
            "receiver_id",
            {
                "taskId": "task_id",
                "userId": "questioning_user",
                "question": "question"
            },
            "question",
            "user_id"), user_object=WeNetUserProfile.empty("receiver_id"), questioning_user=questioning_user, sensitive=True, anonymous=False)
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

        response = handler.handle_nearby_question(QuestionToAnswerMessage(
            "app_id",
            "receiver_id",
            {
                "taskId": "task_id",
                "userId": "questioning_user",
                "question": "question",
                "answer": "yes"
            },
            "question",
            "user_id"), user_object=WeNetUserProfile.empty("receiver_id"), questioning_user=questioning_user, sensitive=False, anonymous=False)
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

        response = handler.handle_question(QuestionToAnswerMessage(
            "app_id",
            "receiver_id",
            {
                "taskId": "task_id",
                "userId": "questioning_user",
                "question": "question"
            },
            "question",
            "user_id"), user_object=WeNetUserProfile.empty("receiver_id"), questioning_user=questioning_user, sensitive=True, anonymous=True)
        self.assertIsInstance(response, TelegramRapidAnswerResponse)
        self.assertEqual(4, len(response.options))
        self.assertEqual(4, len(handler.cache._cache))
        for key in handler.cache._cache:
            cached_item = handler.cache.get(key)
            self.assertEqual("task_id", cached_item["payload"]["task_id"])
            self.assertEqual("question", cached_item["payload"]["question"])
            self.assertEqual(True, cached_item["payload"]["sensitive"])
            self.assertEqual("Anonymous", cached_item["payload"]["username"])

    def test_handle_question_sensitive(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        questioning_user = WeNetUserProfile.empty("questioning_user")
        questioning_user.name.first = "name"
        handler.cache._cache = {}

        response = handler.handle_question(QuestionToAnswerMessage(
            "app_id",
            "receiver_id",
            {
                "taskId": "task_id",
                "userId": "questioning_user",
                "question": "question"
            },
            "question",
            "user_id"), user_object=WeNetUserProfile.empty("receiver_id"), questioning_user=questioning_user, sensitive=True, anonymous=False)
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

        response = handler.handle_question(QuestionToAnswerMessage(
            "app_id",
            "receiver_id",
            {
                "taskId": "task_id",
                "userId": "questioning_user",
                "question": "question",
                "answer": "yes"
            },
            "question",
            "user_id"), user_object=WeNetUserProfile.empty("receiver_id"), questioning_user=questioning_user, sensitive=False, anonymous=False)
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

        question_task = Task("task_id", None, None, "task_type_id", "questioning_user", "app_id", None, TaskGoal("question", ""), attributes={
            "sensitive": True,
            "anonymous": True,
            "positionOfAnswerer": "nearby",
        }, transactions=[TaskTransaction("transaction_id", "task_id", handler.LABEL_ANSWER_TRANSACTION, int(datetime.now().timestamp()), int(datetime.now().timestamp()), "answerer_user", {"answer": "answer", "anonymous": True})])
        response = handler.handle_answered_question(AnsweredQuestionMessage(
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
                "answer": "answer"
            }), user_object=WeNetUserProfile.empty("questioning_user"), answerer_user=answerer_user, question_task=question_task)
        self.assertIsInstance(response, TelegramRapidAnswerResponse)
        self.assertEqual(3, len(response.options))
        self.assertEqual(3, len(handler.cache._cache))
        for key in handler.cache._cache:
            cached_item = handler.cache.get(key)
            self.assertEqual("transaction_id", cached_item["payload"]["transaction_id"])
            self.assertEqual("task_id", cached_item["payload"]["task_id"])

    def test_handle_answered_question_sensitive(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        answerer_user = WeNetUserProfile.empty("answerer_user")
        answerer_user.name.first = "name"
        handler.cache._cache = {}

        question_task = Task("task_id", None, None, "task_type_id", "questioning_user", "app_id", None, TaskGoal("question", ""), attributes={
            "sensitive": True,
            "anonymous": False,
            "positionOfAnswerer": "nearby",
        }, transactions=[TaskTransaction("transaction_id", "task_id", handler.LABEL_ANSWER_TRANSACTION, int(datetime.now().timestamp()), int(datetime.now().timestamp()), "answerer_user", {"answer": "answer", "anonymous": False})])
        response = handler.handle_answered_question(AnsweredQuestionMessage(
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
                "answer": "answer"
            }), user_object=WeNetUserProfile.empty("questioning_user"), answerer_user=answerer_user, question_task=question_task)
        self.assertIsInstance(response, TelegramRapidAnswerResponse)
        self.assertEqual(3, len(response.options))
        self.assertEqual(3, len(handler.cache._cache))
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

        question_task = Task("task_id", None, None, "task_type_id", "questioning_user", "app_id", None, TaskGoal("question", ""), attributes={
            "sensitive": False,
            "anonymous": False,
            "positionOfAnswerer": "nearby",
        }, transactions=[TaskTransaction("transaction_id", "task_id", handler.LABEL_ANSWER_TRANSACTION, int(datetime.now().timestamp()), int(datetime.now().timestamp()), "answerer_user", {"answer": "answer", "anonymous": False})])
        response = handler.handle_answered_question(AnsweredQuestionMessage(
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
                "answer": "answer"
            }), user_object=WeNetUserProfile.empty("questioning_user"), answerer_user=answerer_user, question_task=question_task)
        self.assertIsInstance(response, TelegramRapidAnswerResponse)
        self.assertEqual(3, len(response.options))
        self.assertEqual(3, len(handler.cache._cache))
        for key in handler.cache._cache:
            cached_item = handler.cache.get(key)
            self.assertEqual("transaction_id", cached_item["payload"]["transaction_id"])
            self.assertEqual("task_id", cached_item["payload"]["task_id"])

    def test_action_question_4(self):
        handler = MockAskForHelpHandler()
        translator_instance = TranslatorInstance("wenet-ask-for-help", None, handler._alert_module)
        translator_instance.translate = Mock(return_value="")
        handler._translator.get_translation_instance = Mock(return_value=translator_instance)
        handler._get_user_locale_from_incoming_event = Mock(return_value="en")

        response = handler.action_question_4(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingTextMessage("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", "text"), ConversationContext()), "")
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

        response = handler.action_question_4_1(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", "command", ""), ConversationContext()), handler.INTENT_SENSITIVE_QUESTION)
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

        response = handler.action_question_5(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", "command", ""), ConversationContext()), handler.INTENT_ANONYMOUS_QUESTION)
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

        response = handler.action_question_6(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", "command", ""), ConversationContext()), handler.INTENT_SIMILAR)
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

        response = handler.action_question_final(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", "command", ""), ConversationContext(static_context={
            handler.CONTEXT_WENET_USER_ID: "",
            handler.CONTEXT_ASKED_QUESTION: "question",
            handler.CONTEXT_SOCIAL_CLOSENESS: "similar",
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

        response = handler.action_answer_question(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", "command", ""), ConversationContext(static_context={
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

        response = handler.action_answer_question(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", "command", ""), ConversationContext(static_context={
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
            "sensitive": True,
            "anonymous": True,
            "positionOfAnswerer": "nearby",
        }, transactions=[TaskTransaction("transaction_id", "task_id", handler.LABEL_ANSWER_TRANSACTION, int(datetime.now().timestamp()), int(datetime.now().timestamp()), "answerer_user", {"answer": "answer", "anonymous": True})]))
        handler._get_service_api_interface_connector_from_context = Mock(return_value=service_api)

        response = handler.action_answer_picked_question(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", "command", ""), ConversationContext(static_context={
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
            "sensitive": False,
            "anonymous": False,
            "positionOfAnswerer": "nearby",
        }, transactions=[TaskTransaction("transaction_id", "task_id", handler.LABEL_ANSWER_TRANSACTION, int(datetime.now().timestamp()), int(datetime.now().timestamp()), "answerer_user", {"answer": "answer", "anonymous": True})]))
        handler._get_service_api_interface_connector_from_context = Mock(return_value=service_api)

        response = handler.action_answer_picked_question(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", "command", ""), ConversationContext(static_context={
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

        response = handler.action_answer_question_anonymously(IncomingTelegramEvent("", TelegramDetails(1, 1, ""), IncomingCommand("message_id", int(datetime.now().timestamp()), "user_id", "chat_id", "command", ""), ConversationContext(static_context={
            handler.CONTEXT_QUESTION_TO_ANSWER: "task_id",
            handler.CONTEXT_ANSWER_TO_QUESTION: "answer",
            handler.CONTEXT_WENET_USER_ID: "user_id"
        })), handler.INTENT_ANSWER_ANONYMOUSLY)
        self.assertIsInstance(response, OutgoingEvent)
        self.assertEqual(1, len(response.messages))
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
        self.assertEqual(1, len(response.messages))
        self.assertIsInstance(response.messages[0], TextualResponse)
