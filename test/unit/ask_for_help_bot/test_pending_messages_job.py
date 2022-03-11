from __future__ import absolute_import, annotations

import datetime
from unittest import TestCase
from unittest.mock import Mock

from chatbot_core.model.context import ConversationContext
from chatbot_core.model.details import TelegramDetails
from chatbot_core.model.user_context import UserConversationContext
from chatbot_core.v3.connector.chatbot_interface import ChatbotInterfaceConnectorV3
from chatbot_core.v3.connector.social_connectors.telegram_connector import TelegramSocialConnector
from chatbot_core.v3.model.messages import TelegramTextualResponse
from chatbot_core.v3.model.outgoing_event import NotificationEvent

from ask_for_help_bot.pending_conversations import PendingQuestionToAnswer
from ask_for_help_bot.pending_messages_job import PendingMessagesJob


class TestPendingMessagesJob(TestCase):

    def test_handle_remind_me_later_messages(self):
        pending_question_to_answer = PendingQuestionToAnswer("question_id", TelegramTextualResponse("text"), TelegramDetails(1, 1, "telegram_bot_id"),
                                                             sent=datetime.datetime.now() - datetime.timedelta(minutes=PendingMessagesJob.REMINDER_MINUTES))
        context = UserConversationContext(
            social_details=TelegramDetails(1, 1, "telegram_bot_id"),
            context=ConversationContext(static_context={PendingMessagesJob.CONTEXT_PENDING_ANSWERS: {"question_id": pending_question_to_answer.to_repr()}})
        )

        ChatbotInterfaceConnectorV3.build_from_env = Mock()
        message_job = PendingMessagesJob("job_id", "instance_namespace", TelegramSocialConnector("bot_token"), logger_connectors=None)
        message_job.send_notification = Mock()
        message_job._interface_connector.update_user_context = Mock()
        message_job._handle_remind_me_later_messages(context)

        message_job.send_notification.assert_called_once()
        message_job.send_notification.assert_called_with(NotificationEvent(
            social_details=pending_question_to_answer.social_details,
            messages=[pending_question_to_answer.response],
            context=context.context
        ))
        message_job._interface_connector.update_user_context.assert_called_once()
        message_job._interface_connector.update_user_context.assert_called_with(UserConversationContext(
            social_details=TelegramDetails(1, 1, "telegram_bot_id"),
            context=ConversationContext(static_context={PendingMessagesJob.CONTEXT_PENDING_ANSWERS: {}})
        ))

    def test_handle_remind_me_later_messages_wrong_repr(self):
        pending_question_to_answer = {"question_id": "question_id"}
        context = UserConversationContext(
            social_details=TelegramDetails(1, 1, "telegram_bot_id"),
            context=ConversationContext(static_context={PendingMessagesJob.CONTEXT_PENDING_ANSWERS: {"question_id": pending_question_to_answer}})
        )

        ChatbotInterfaceConnectorV3.build_from_env = Mock()
        message_job = PendingMessagesJob("job_id", "instance_namespace", TelegramSocialConnector("bot_token"), logger_connectors=None)
        message_job.send_notification = Mock()
        message_job._interface_connector.update_user_context = Mock()
        message_job._handle_remind_me_later_messages(context)

        message_job.send_notification.assert_not_called()
        message_job._interface_connector.update_user_context.assert_called_once()
        message_job._interface_connector.update_user_context.assert_called_with(UserConversationContext(
            social_details=TelegramDetails(1, 1, "telegram_bot_id"),
            context=ConversationContext(static_context={PendingMessagesJob.CONTEXT_PENDING_ANSWERS: {}})
        ))

    def test_handle_remind_me_later_messages_exception_sending_message(self):
        pending_question_to_answer = PendingQuestionToAnswer("question_id", TelegramTextualResponse("text"), TelegramDetails(1, 1, "telegram_bot_id"),
                                                             sent=datetime.datetime.now() - datetime.timedelta(minutes=PendingMessagesJob.REMINDER_MINUTES))
        context = UserConversationContext(
            social_details=TelegramDetails(1, 1, "telegram_bot_id"),
            context=ConversationContext(static_context={PendingMessagesJob.CONTEXT_PENDING_ANSWERS: {"question_id": pending_question_to_answer.to_repr()}})
        )

        ChatbotInterfaceConnectorV3.build_from_env = Mock()
        message_job = PendingMessagesJob("job_id", "instance_namespace", TelegramSocialConnector("bot_token"), logger_connectors=None)
        message_job.send_notification = Mock(return_value=Exception("exception sending message"))
        message_job._interface_connector.update_user_context = Mock()
        message_job._handle_remind_me_later_messages(context)

        message_job.send_notification.assert_called_once()
        message_job.send_notification.assert_called_with(NotificationEvent(
            social_details=pending_question_to_answer.social_details,
            messages=[pending_question_to_answer.response],
            context=context.context
        ))
        message_job._interface_connector.update_user_context.assert_called_once()
        message_job._interface_connector.update_user_context.assert_called_with(UserConversationContext(
            social_details=TelegramDetails(1, 1, "telegram_bot_id"),
            context=ConversationContext(static_context={PendingMessagesJob.CONTEXT_PENDING_ANSWERS: {}})
        ))