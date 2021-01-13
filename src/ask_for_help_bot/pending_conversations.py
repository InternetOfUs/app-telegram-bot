from __future__ import absolute_import, annotations

from datetime import datetime
from typing import Optional

from chatbot_core.model.details import SocialDetails
from chatbot_core.v3.model.messages import ResponseMessage


class PendingQuestionToAnswer:
    """
    This class is a pending question to be answered. It contains:
    - the question ID
    - the TelegramRapidAnswerResponse showed to the user with 4 buttons
    - the timestamp of when the 'remind me later' button is clicked
    """

    def __init__(self, question_id: str, response: ResponseMessage, social_details: SocialDetails,
                 added: Optional[datetime] = None, sent: Optional[datetime] = None) -> None:
        self.question_id = question_id
        self.response = response
        self.sent = sent
        self.social_details = social_details
        self.added = added
        if not self.added:
            self.added = datetime.now()

    def to_repr(self) -> dict:
        return {
            "question_id": self.question_id,
            "response": self.response.to_repr(),
            "sent": self.sent.isoformat() if self.sent else None,
            "added": self.added.isoformat() if self.added else None,
            "social_details": self.social_details.to_repr(),
        }

    @staticmethod
    def from_repr(raw: dict) -> PendingQuestionToAnswer:
        return PendingQuestionToAnswer(
            raw["question_id"],
            ResponseMessage.from_repr(raw["response"]),
            SocialDetails.from_repr(raw["social_details"]),
            datetime.fromisoformat(raw["added"]) if raw["added"] else None,
            datetime.fromisoformat(raw["sent"]) if raw["sent"] else None
        )

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, PendingQuestionToAnswer):
            return False
        return self.question_id == o.question_id and self.response == o.response and \
            self.social_details == o.social_details and self.added == o.added and self.sent == o.sent
