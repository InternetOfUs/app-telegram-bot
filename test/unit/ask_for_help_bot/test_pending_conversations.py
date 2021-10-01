from datetime import datetime
from unittest import TestCase

from ask_for_help_bot.pending_conversations import PendingQuestionToAnswer
from chatbot_core.model.details import TelegramDetails
from chatbot_core.v3.model.messages import TelegramRapidAnswerResponse, TextualResponse


class TestPendingQuestionToAnswer(TestCase):

    def test_repr(self):
        message = TelegramRapidAnswerResponse(TextualResponse("message"))
        message.with_textual_option("text", "payload")
        social_details = TelegramDetails(1, 1, "bot_id")
        pending_conversation = PendingQuestionToAnswer("question_id", message, social_details, datetime.now())
        self.assertEqual(PendingQuestionToAnswer.from_repr(pending_conversation.to_repr()), pending_conversation)
