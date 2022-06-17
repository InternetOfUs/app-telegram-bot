from chatbot_core.model.context import ConversationContext


class StateMixin:

    # context current state
    CONTEXT_CURRENT_STATE = "current_state"
    # context for wenet messages and pending answers
    CONTEXT_PENDING_WENET_MESSAGES = "pending_wenet_messages"
    CONTEXT_PENDING_ANSWERS = "pending_answers"
    # available states
    STATE_QUESTION_0 = "question_0"
    STATE_QUESTION_1 = "question_1"
    STATE_QUESTION_2 = "question_2"
    STATE_QUESTION_3 = "question_3"
    STATE_ANSWERING = "answer_2"
    STATE_ANSWERING_SENSITIVE = "answer_sensitive"
    STATE_ANSWERING_ANONYMOUSLY = "answer_anonymously"
    STATE_PUBLISHING_ANSWER_TO_CHANNEL = "publishing_answer_to_channel"
    STATE_BEST_ANSWER_0 = "best_answer_0"
    STATE_BEST_ANSWER_PUBLISH = "best_answer_publish"
    STATE_BEST_ANSWER_1 = "best_answer_1"

    def _is_doing_another_action(self, context: ConversationContext) -> bool:
        """
        Returns True if the user is in another action (e.g. inside the /ask flow), False otherwise
        """
        statuses = [
            self.STATE_ANSWERING, self.STATE_ANSWERING_SENSITIVE, self.STATE_ANSWERING_ANONYMOUSLY,
            self.STATE_QUESTION_0, self.STATE_QUESTION_1, self.STATE_QUESTION_2, self.STATE_QUESTION_3,
            self.STATE_BEST_ANSWER_0, self.STATE_BEST_ANSWER_PUBLISH, self.STATE_PUBLISHING_ANSWER_TO_CHANNEL,
            self.STATE_BEST_ANSWER_1
        ]
        current_status = context.get_static_state(self.CONTEXT_CURRENT_STATE, "")
        return current_status in statuses
