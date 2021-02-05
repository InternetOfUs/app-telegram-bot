import datetime
from typing import Optional, List

from ask_for_help_bot.pending_conversations import PendingQuestionToAnswer
from chatbot_core.model.user_context import UserConversationContext
from chatbot_core.v3.connector.social_connector import SocialConnector
from chatbot_core.v3.job.job import SocialJob
from chatbot_core.v3.logger.event_logger import LoggerConnector
from chatbot_core.v3.model.outgoing_event import NotificationEvent


class PendingMessagesJob(SocialJob):
    """
    This job passes all the contexts, checking whether they contain a pending question dictionaries.
    In case they do, and the right amount of time since the question was added is passed,
    the stored message is sent to the user, and the pending question removed from the dict.

    It also cleans the pending messages: if a message is pending for more than `REMOVE_AFTER_MINUTES`- meaning that
    a user has not used the bot anymore - the message is removed
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
            self._handle_remind_me_later_messages(context)

    def _handle_remind_me_later_messages(self, context: UserConversationContext) -> None:
        """
        Check whether a context contains some pending answers. In case they do, they are handled:
        - either sending the pending message
        - or removing the pending message, in case it is too old
        """
        notifications = []
        pending_answers = context.context.get_static_state(self.CONTEXT_PENDING_ANSWERS, dict())
        to_remove = set()
        modified = False
        for question_id in pending_answers:
            pending_answer = PendingQuestionToAnswer.from_repr(pending_answers[question_id])
            if pending_answer.sent is not None and pending_answer.sent + \
                    datetime.timedelta(minutes=self.REMINDER_MINUTES) > datetime.datetime.now():
                # pretending to be in the same state as if the bot receives a new message from Wenet
                context.context.with_static_state("current_state", "answer_1")
                # adding the question id in the context
                context.context.with_static_state("question_to_answer", pending_answer.question_id)
                # keep the pending question, removing only the 'sent' timestamp
                pending_answer.sent = None
                pending_answers[question_id] = pending_answer.to_repr()
                notifications.append(NotificationEvent(pending_answer.social_details, [pending_answer.response]))
                modified = True
        for question_id in to_remove:
            pending_answers.pop(question_id)
        if modified:
            context.context.with_static_state(self.CONTEXT_PENDING_ANSWERS, pending_answers)
            self._interface_connector.update_user_context(context)

        for notification in notifications:
            notification.with_context(context.context)
            self.send_notification(notification)
