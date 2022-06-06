from __future__ import absolute_import, annotations
from wenet.model.callback_message.message import Message, IncentiveBadge, IncentiveMessage, TaskSelectionNotification, \
    TaskProposalNotification, TaskVolunteerNotification, TaskConcludedNotification, TextualMessage, \
    QuestionToAnswerMessage, AnsweredQuestionMessage, AnsweredPickedMessage


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
            - list_of_transaction_ids: The ids of the transactions associated with the answer
    """
    LABEL = "QuestionExpirationMessage"

    def __init__(self, app_id: str, receiver_id: str, task_id: str, question: str, transaction_ids: list, attributes: dict) -> None:
        attributes.update({
            "taskId": task_id,
            "question": question,
            "listOfTransactionIds": transaction_ids,
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
            raw["attributes"]
        )

    @property
    def task_id(self) -> str:
        return self.attributes["taskId"]

    @property
    def question(self) -> str:
        return self.attributes["question"]

    @property
    def list_of_transaction_ids(self) -> str:
        return self.attributes["listOfTransactionIds"]


class MessageBuilder:

    @staticmethod
    def build(raw_message: dict) -> Message:
        """
        It may raise ValueError or KeyError, to be caught where this method is used

        :param raw_message: the raw message representation
        :return Message: the message model
        :raises ValueError KeyError:
        """
        message_label = raw_message["label"]
        if message_label == TextualMessage.LABEL:
            message = TextualMessage.from_repr(raw_message)
        elif message_label == TaskConcludedNotification.LABEL:
            message = TaskConcludedNotification.from_repr(raw_message)
        elif message_label == TaskVolunteerNotification.LABEL:
            message = TaskVolunteerNotification.from_repr(raw_message)
        elif message_label == TaskProposalNotification.LABEL:
            message = TaskProposalNotification.from_repr(raw_message)
        elif message_label == TaskSelectionNotification.LABEL:
            message = TaskSelectionNotification.from_repr(raw_message)
        elif message_label == IncentiveMessage.LABEL:
            message = IncentiveMessage.from_repr(raw_message)
        elif message_label == IncentiveBadge.LABEL:
            message = IncentiveBadge.from_repr(raw_message)
        elif message_label == QuestionExpirationMessage.LABEL:
            message = QuestionExpirationMessage.from_repr(raw_message)
        elif message_label == "INCENTIVE":
            if "IncentiveType" in raw_message["attributes"] and raw_message["attributes"]["IncentiveType"] == "Message":
                message = IncentiveMessage.from_repr(raw_message)
            elif "IncentiveType" in raw_message["attributes"] and raw_message["attributes"]["IncentiveType"] == "Badge":
                message = IncentiveBadge.from_repr(raw_message)
            else:
                message = Message.from_repr(raw_message)
        elif message_label == QuestionToAnswerMessage.LABEL:
            message = QuestionToAnswerMessage.from_repr(raw_message)
        elif message_label == AnsweredQuestionMessage.LABEL:
            message = AnsweredQuestionMessage.from_repr(raw_message)
        elif message_label == AnsweredPickedMessage.LABEL:
            return AnsweredPickedMessage.from_repr(raw_message)
        else:
            message = Message.from_repr(raw_message)
        return message

# TODO maybe implement another QuestionToAnswer callback? (with domains)