from datetime import datetime
from unittest import TestCase

from ask_for_help_bot.pending_conversations import PendingQuestionToAnswer, PendingWenetMessage
from chatbot_core.model.details import TelegramDetails
from chatbot_core.v3.model.messages import TelegramRapidAnswerResponse, TextualResponse


class TestPendingWenetMessage(TestCase):

    def test_repr(self):
        message = TelegramRapidAnswerResponse(TextualResponse("message"))
        message.with_textual_option("text", "payload")
        social_details = TelegramDetails(1, 1, "bot_id")
        pending_wenet_message = PendingWenetMessage("pending_wenet_message_id", [message], social_details)
        self.assertEqual(PendingWenetMessage.from_repr(pending_wenet_message.to_repr()), pending_wenet_message)


class TestPendingQuestionToAnswer(TestCase):

    def test_repr(self):
        message = TelegramRapidAnswerResponse(TextualResponse("message"))
        message.with_textual_option("text", "payload")
        social_details = TelegramDetails(1, 1, "bot_id")
        pending_question = PendingQuestionToAnswer("question_id", message, social_details, datetime.now())
        self.assertEqual(PendingQuestionToAnswer.from_repr(pending_question.to_repr()), pending_question)
