from __future__ import absolute_import, annotations
from wenet.model.callback_message.message import Message


class QuestionExpirationMessage(Message):
    """
    Message received when question is expired

    Attributes:
        - app_id: ID of the Wenet application related to the message
        - receiver_id: The Wenet user ID of the recipient of the message
        - label: The type of the message
        - attributes: dictionary with additional attributes of the message. It may contain
            - task_id: The identifier of the target task
            - question: The question to be answered
            - user_id: The author of the question
            - transaction_id: The ids of the transactions associated with the answer
    """
    LABEL = "QuestionExpirationMessage"

    def __init__(self, app_id: str, receiver_id: str, task_id: str, question: str, user_id: str, transaction_ids: list, attributes: dict) -> None:
        attributes.update({
            "taskId": task_id,
            "question": question,
            "listOfTransactionIds": transaction_ids,
            "userId": user_id,
        })
        super().__init__(app_id, receiver_id, self.LABEL, attributes)

    @staticmethod
    def from_repr(raw: dict) -> QuestionExpirationMessage:
        return QuestionExpirationMessage(
            raw["appId"],
            raw["receiverId"],
            raw["attributes"]["taskId"],
            raw["attributes"]["question"],
            raw["attributes"]["listOfTransactionIds"],
            raw["attributes"]["userId"],
            raw["attributes"]
        )

    @property
    def task_id(self) -> str:
        return self.attributes["taskId"]

    @property
    def question(self) -> str:
        return self.attributes["question"]

    @property
    def user_id(self) -> str:
        return self.attributes["userId"]

    @property
    def list_of_transaction_ids(self) -> str:
        return self.attributes["listOfTransactionIds"]


