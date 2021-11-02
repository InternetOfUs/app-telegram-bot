from __future__ import absolute_import, annotations

import datetime
import logging
from typing import Optional, List, Dict, Set

from ask_for_help_bot.pending_conversations import PendingQuestionToAnswer
from chatbot_core.model.user_context import UserConversationContext
from chatbot_core.v3.connector.social_connector import SocialConnector
from chatbot_core.v3.job.job import SocialJob
from chatbot_core.v3.logger.event_logger import LoggerConnector
from chatbot_core.v3.model.outgoing_event import NotificationEvent


logger = logging.getLogger("uhopper.chatbot.wenet.askforhelp.pending_messages_job")


class PendingMessagesJob(SocialJob):
    """
    This job passes all the contexts, checking whether they contain a pending question dictionaries.
    In case they do, and the right amount of time since the question was added is passed,
    the stored message is sent to the user, and the pending question removed from the dict.
    """
    CONTEXT_PENDING_ANSWERS = "pending_answers"
    REMINDER_MINUTES = 60

    def __init__(self, job_id, instance_namespace: str, connector: SocialConnector,
                 logger_connectors: Optional[List[LoggerConnector]]):
        super().__init__(job_id, instance_namespace, connector, logger_connectors)

    def _should_run(self) -> bool:
        return True

    def execute(self, **kwargs) -> None:
        contexts = self._interface_connector.get_user_contexts(self._instance_namespace, None)
        for context in contexts:
            try:
                self._handle_remind_me_later_messages(context)
            except Exception as e:
                logger.exception(f"An exception [{type(e)}] occurs handling the context [{context}]", exc_info=e)

    def _handle_remind_me_later_messages(self, context: UserConversationContext) -> None:
        """
        Check whether a context contains some pending questions. In case they do, they are handled sending the
        pending questions and removing the questions from the dict.
        """
        notifications: List[NotificationEvent] = []
        pending_answers: Dict[str, dict] = context.context.get_static_state(self.CONTEXT_PENDING_ANSWERS, dict())
        questions_to_remove: Set[str] = set()
        is_context_modified: bool = False
        for question_id in pending_answers:
            try:
                pending_answer = PendingQuestionToAnswer.from_repr(pending_answers[question_id])
            except Exception as e:
                logger.exception(f"An exception [{type(e)}] occurs handling in parsing the pending answer [{pending_answers[question_id]}]", exc_info=e)
                questions_to_remove.add(question_id)
                is_context_modified = True
                continue

            if pending_answer.sent is not None and pending_answer.sent + datetime.timedelta(minutes=self.REMINDER_MINUTES) <= datetime.datetime.now():
                notifications.append(NotificationEvent(social_details=pending_answer.social_details, messages=[pending_answer.response]))
                questions_to_remove.add(pending_answer.question_id)
                is_context_modified = True

        for notification in notifications:
            notification.with_context(context.context)
            try:
                self.send_notification(notification)
            except Exception as e:
                logger.exception(f"An exception [{type(e)}] occurs sending the notification [{notification}]", exc_info=e)

        for question_id in questions_to_remove:
            pending_answers.pop(question_id)

        if is_context_modified:
            context.context.with_static_state(self.CONTEXT_PENDING_ANSWERS, pending_answers)
            self._interface_connector.update_user_context(context)
