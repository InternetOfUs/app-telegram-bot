from datetime import datetime
from unittest import TestCase
from unittest.mock import Mock

from chatbot_core.translator.translator import TranslatorInstance
from chatbot_core.v3.model.messages import TelegramRapidAnswerResponse
from wenet.model.callback_message.message import QuestionToAnswerMessage, AnsweredQuestionMessage
from wenet.model.task.task import Task, TaskGoal
from wenet.model.task.transaction import TaskTransaction
from wenet.model.user.profile import WeNetUserProfile

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
            }), user_object=WeNetUserProfile.empty("questioning_user"), answerer_user=answerer_user,
            question_task=question_task)
        self.assertIsInstance(response, TelegramRapidAnswerResponse)
        self.assertEqual(3, len(response.options))
        self.assertEqual(3, len(handler.cache._cache))
        for key in handler.cache._cache:
            cached_item = handler.cache.get(key)
            self.assertEqual("transaction_id", cached_item["payload"]["transaction_id"])
            self.assertEqual("task_id", cached_item["payload"]["task_id"])
