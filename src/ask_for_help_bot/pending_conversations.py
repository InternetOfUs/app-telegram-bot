from __future__ import absolute_import, annotations

from datetime import datetime
from typing import Optional, List

from chatbot_core.model.details import SocialDetails
from chatbot_core.v3.model.messages import ResponseMessage


class PendingWenetMessage:
    """
    This class is a pending message from WeNet to be sent. It contains:
    - the ID
    - the response messages to be sent to the user
    - the social details of the user
    """

    def __init__(self, pending_wenet_message_id: str, responses: List[ResponseMessage], social_details: SocialDetails) -> None:
        self.pending_wenet_message_id = pending_wenet_message_id
        self.responses = responses
        self.social_details = social_details

    def to_repr(self) -> dict:
        return {
            "pending_wenet_message_id": self.pending_wenet_message_id,
            "responses": [response.to_repr() for response in self.responses],
            "social_details": self.social_details.to_repr(),
        }

    @staticmethod
    def from_repr(raw: dict) -> PendingWenetMessage:
        return PendingWenetMessage(
            raw["pending_wenet_message_id"],
            [ResponseMessage.from_repr(response) for response in raw["responses"]],
            SocialDetails.from_repr(raw["social_details"])
        )

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, PendingWenetMessage):
            return False
        return self.pending_wenet_message_id == o.pending_wenet_message_id and self.responses == o.responses and \
            self.social_details == o.social_details


class PendingQuestionToAnswer:
    """
    This class is a pending question to be answered. It contains:
    - the question ID
    - the response containing the pending question to be sent to the user
    - the social details of the user
    - the timestamp of when the 'remind me later' button is clicked
    """

    def __init__(self, question_id: str, response: ResponseMessage, social_details: SocialDetails,
                 sent: Optional[datetime] = None) -> None:
        self.question_id = question_id
        self.response = response
        self.social_details = social_details
        self.sent = sent

    def to_repr(self) -> dict:
        return {
            "question_id": self.question_id,
            "response": self.response.to_repr(),
            "social_details": self.social_details.to_repr(),
            "sent": self.sent.isoformat() if self.sent else None
        }

    @staticmethod
    def from_repr(raw: dict) -> PendingQuestionToAnswer:
        return PendingQuestionToAnswer(
            raw["question_id"],
            ResponseMessage.from_repr(raw["response"]),
            SocialDetails.from_repr(raw["social_details"]),
            sent=datetime.fromisoformat(raw["sent"]) if raw.get("sent") else None
        )

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, PendingQuestionToAnswer):
            return False
        return self.question_id == o.question_id and self.response == o.response and \
            self.social_details == o.social_details and self.sent == o.sent
