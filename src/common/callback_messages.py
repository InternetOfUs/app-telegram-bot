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


class TextualMessage(Message):
    """
    A simple textual message from WeNet to the user.

    Attributes:
        - app_id: ID of the Wenet application related to the message
        - receiver_id: The Wenet user ID of the recipient of the message
        - title: The title of the message
        - text: the content of the message
        - attributes: dictionary with additional attributes of the message. It may contain
            - community_id: ID of the community related to the message
            - task_id: The identifier of the target task
    """
    LABEL = "TextualMessage"

    def __init__(self, app_id: str, receiver_id: str, title: str, text: str, attributes: dict) -> None:
        attributes.update({
            "title": title,
            "text": text,
        })
        super().__init__(app_id, receiver_id, self.LABEL, attributes)

    @property
    def text(self) -> str:
        return self.attributes["text"]

    @property
    def title(self) -> str:
        return self.attributes["title"]

    @staticmethod
    def from_repr(raw: dict) -> TextualMessage:
        return TextualMessage(
            raw["appId"],
            raw["receiverId"],
            raw["attributes"]["title"],
            raw["attributes"]["text"],
            raw["attributes"]
        )


class TaskProposalNotification(Message):
    """
    This notification is used in order to propose a user to volunteer to a newly created task

    Attributes:
        - app_id: ID of the Wenet application related to the message
        - receiver_id: The Wenet user ID of the recipient of the message
        - attributes: dictionary with additional attributes of the message. It may contain
            - community_id: ID of the community related to the message
            - task_id: The identifier of the target task
    """
    LABEL = "TaskProposalNotification"

    def __init__(self, app_id: str, receiver_id: str, attributes: dict) -> None:
        super().__init__(app_id, receiver_id, self.LABEL, attributes)

    @staticmethod
    def from_repr(raw: dict) -> TaskProposalNotification:
        return TaskProposalNotification(
            raw["appId"],
            raw["receiverId"],
            raw["attributes"]
        )


class TaskVolunteerNotification(Message):
    """
    This notification is used in order to notify the task creator that a new volunteer is proposing to participate
    to the task.

    Attributes:
        - app_id: ID of the Wenet application related to the message
        - receiver_id: The Wenet user ID of the recipient of the message
        - volunteer_id: The Wenet user ID of the volunteer
        - attributes: dictionary with additional attributes of the message. It may contain
            - community_id: ID of the community related to the message
            - task_id: The identifier of the target task
    """
    LABEL = "TaskVolunteerNotification"

    def __init__(self, app_id: str, receiver_id: str, volunteer_id: str, attributes: dict) -> None:
        attributes.update({"volunteerId": volunteer_id})
        super().__init__(app_id, receiver_id, self.LABEL, attributes)

    @staticmethod
    def from_repr(raw: dict) -> TaskVolunteerNotification:
        return TaskVolunteerNotification(
            raw["appId"],
            raw["receiverId"],
            raw["attributes"]["volunteerId"],
            raw["attributes"]
        )

    @property
    def volunteer_id(self) -> str:
        return self.attributes["volunteerId"]


class TaskSelectionNotification(Message):
    """
    This notification is used in order to notify the user who volunteered about the decision of the task creator.

    Attributes:
        - app_id: ID of the Wenet application related to the message
        - receiver_id: The Wenet user ID of the recipient of the message
        - outcome: The outcome of the selection, either 'accepted' or 'refused'
        - attributes: dictionary with additional attributes of the message. It may contain
            - community_id: ID of the community related to the message
            - task_id: The identifier of the target task
    """
    LABEL = "TaskSelectionNotification"
    OUTCOME_ACCEPTED = 'accepted'
    OUTCOME_REFUSED = 'refused'

    def __init__(self, app_id: str, receiver_id: str, outcome: str, attributes: dict) -> None:
        accepted_outcomes = [self.OUTCOME_ACCEPTED, self.OUTCOME_REFUSED]
        if outcome not in accepted_outcomes:
            raise ValueError(f"Outcome must be one of {accepted_outcomes}, got [{outcome}]")
        attributes.update({"outcome": outcome})
        super().__init__(app_id, receiver_id, self.LABEL, attributes)

    @staticmethod
    def from_repr(raw: dict) -> TaskSelectionNotification:
        return TaskSelectionNotification(
            raw["appId"],
            raw["receiverId"],
            raw["attributes"]["outcome"],
            raw["attributes"]
        )

    @property
    def outcome(self) -> str:
        return self.attributes["outcome"]


class TaskConcludedNotification(Message):
    """
    This notification is used in order to notify task participants that a task has been completed, the outcome could be:
        - completed (if completed correctly)
        - failed (if something went wrong)
        - cancelled (the creator cancelled the task)

    Attributes:
        - app_id: ID of the Wenet application related to the message
        - receiver_id: The Wenet user ID of the recipient of the message
        - outcome: The outcome of the task
        - attributes: dictionary with additional attributes of the message. It may contain
            - community_id: ID of the community related to the message
            - task_id: The identifier of the target task
    """
    LABEL = "TaskConcludedNotification"
    OUTCOME_COMPLETED = "completed"
    OUTCOME_CANCELLED = "cancelled"
    OUTCOME_FAILED = "failed"

    def __init__(self, app_id: str, receiver_id: str, outcome: str, attributes: dict) -> None:
        accepted_outcomes = [self.OUTCOME_COMPLETED, self.OUTCOME_CANCELLED, self.OUTCOME_FAILED]
        if outcome not in accepted_outcomes:
            raise ValueError(f"Outcome must be one of {accepted_outcomes}, got [{outcome}]")
        attributes.update({"outcome": outcome})
        super().__init__(app_id, receiver_id, self.LABEL, attributes)

    @staticmethod
    def from_repr(raw: dict) -> TaskConcludedNotification:
        return TaskConcludedNotification(
            raw["appId"],
            raw["receiverId"],
            raw["attributes"]["outcome"],
            raw["attributes"]
        )

    @property
    def outcome(self) -> str:
        return self.attributes["outcome"]


class IncentiveMessage(Message):
    """
    This message is used to send an incentive to an user.

    Attributes:
        - app_id: ID of the Wenet application related to the message
        - receiver_id: The Wenet user ID of the recipient of the message
        - issuer: the issuer of the incentive
        - content: the content of the incentive
        - attributes: dictionary with additional attributes of the message. It may contain
            - community_id: ID of the community related to the message
            - task_id: The identifier of the target task
    """
    LABEL = "IncentiveMessage"

    def __init__(self, app_id: str, receiver_id: str, issuer: str, content: str, attributes: dict) -> None:
        attributes.update({
            "issuer": issuer,
            "content": content,
        })
        super().__init__(app_id, receiver_id, self.LABEL, attributes)

    @staticmethod
    def from_repr(raw: dict) -> IncentiveMessage:
        return IncentiveMessage(
            raw["appId"],
            raw["receiverId"],
            raw["attributes"]["issuer"] if "issuer" in raw["attributes"] else raw["attributes"]["Issuer"],
            raw["attributes"]["content"] if "content" in raw["attributes"] else raw["attributes"]["Message"]["content"],
            raw["attributes"]
        )

    @property
    def issuer(self) -> str:
        return self.attributes["issuer"]

    @property
    def content(self) -> str:
        return self.attributes["content"]


class IncentiveBadge(Message):
    """
    This message is used to send a badge to an user.

    Attributes:
        - app_id: ID of the Wenet application related to the message
        - receiver_id: The Wenet user ID of the recipient of the message
        - issuer: the issuer of the incentive
        - badge_class: the class of the badge
        - image_url: the URL of the image of the badge
        - criteria: the criteria with which the badge was given
        - message: the content of the incentive
        - attributes: dictionary with additional attributes of the message. It may contain
            - community_id: ID of the community related to the message
            - task_id: The identifier of the target task
    """
    LABEL = "IncentiveBadge"

    def __init__(self, app_id: str, receiver_id: str, issuer: str, badge_class: str, image_url: str, criteria: str,
                 message: str, attributes: dict) -> None:
        attributes.update({
            "issuer": issuer,
            "badgeClass": badge_class,
            "imageUrl": image_url,
            "criteria": criteria,
            "message": message,
        })
        super().__init__(app_id, receiver_id, self.LABEL, attributes)

    @staticmethod
    def from_repr(raw: dict) -> IncentiveBadge:
        return IncentiveBadge(
            raw["appId"],
            raw["receiverId"],
            raw["attributes"]["issuer"] if "issuer" in raw["attributes"] else raw["attributes"]["Issuer"],
            raw["attributes"]["badgeClass"] if "badgeClass" in raw["attributes"] else raw["attributes"]["Badge"]["BadgeClass"],
            raw["attributes"]["imageUrl"] if "imageUrl" in raw["attributes"] else raw["attributes"]["Badge"]["ImgUrl"],
            raw["attributes"]["criteria"] if "criteria" in raw["attributes"] else raw["attributes"]["Badge"]["Criteria"],
            raw["attributes"]["message"] if "message" in raw["attributes"] else raw["attributes"]["Badge"]["Message"],
            raw["attributes"]
        )

    @property
    def issuer(self) -> str:
        return self.attributes["issuer"]

    @property
    def badge_class(self) -> str:
        return self.attributes["badgeClass"]

    @property
    def image_url(self) -> str:
        return self.attributes["imageUrl"]

    @property
    def criteria(self) -> str:
        return self.attributes["criteria"]

    @property
    def message(self) -> str:
        return self.attributes["message"]


class QuestionToAnswerMessage(Message):
    """
    Message containing a new question to be answered.

    Attributes:
        - app_id: ID of the Wenet application related to the message
        - receiver_id: The Wenet user ID of the recipient of the message
        - label: The type of the message
        - attributes: dictionary with additional attributes of the message. It may contain
            - community_id: ID of the community related to the message
            - task_id: The identifier of the target task
            - question: The question to be answered
            - user_id: The author of the question
    """
    LABEL = "QuestionToAnswerMessage"

    def __init__(self, app_id: str, receiver_id: str, attributes: dict, question: str, user_id: str) -> None:
        attributes.update({
            "question": question,
            "userId": user_id,
        })
        super().__init__(app_id, receiver_id, self.LABEL, attributes)

    @staticmethod
    def from_repr(raw: dict) -> QuestionToAnswerMessage:
        return QuestionToAnswerMessage(
            raw["appId"],
            raw["receiverId"],
            raw["attributes"],
            raw["attributes"]["question"],
            raw["attributes"]["userId"]
        )

    @property
    def question(self) -> str:
        return self.attributes["question"]

    @property
    def user_id(self) -> str:
        return self.attributes["userId"]


class AnsweredQuestionMessage(Message):
    """
    Message containing a new answer to a question.

    Attributes:
        - app_id: ID of the Wenet application related to the message
        - receiver_id: The Wenet user ID of the recipient of the message
        - label: The type of the message
        - attributes: dictionary with additional attributes of the message. It may contain
            - community_id: ID of the community related to the message
            - task_id: The identifier of the target task
            - answer: The answer to the question
            - userId: The author of the question
            - transaction_id: The id of the transaction associated with the answer
    """
    LABEL = "AnsweredQuestionMessage"

    def __init__(self, app_id: str, receiver_id: str, answer: str, transaction_id: str, user_id: str,
                 attributes: dict) -> None:
        attributes.update({
            "answer": answer,
            "transactionId": transaction_id,
            "userId": user_id,
        })
        super().__init__(app_id, receiver_id, self.LABEL, attributes)

    @staticmethod
    def from_repr(raw: dict) -> AnsweredQuestionMessage:
        return AnsweredQuestionMessage(
            raw["appId"],
            raw["receiverId"],
            raw["attributes"]["answer"],
            raw["attributes"]["transactionId"],
            raw["attributes"]["userId"],
            raw["attributes"]
        )

    @property
    def answer(self) -> str:
        return self.attributes["answer"]

    @property
    def transaction_id(self) -> str:
        return self.attributes["transactionId"]

    @property
    def user_id(self) -> str:
        return self.attributes["userId"]


class AnsweredPickedMessage(Message):
    """
    Message received when an answer is picked as the best one.

    Attributes:
        - app_id: ID of the Wenet application related to the message
        - receiver_id: The Wenet user ID of the recipient of the message
        - label: The type of the message
        - attributes: dictionary with additional attributes of the message. It may contain
            - community_id: ID of the community related to the message
            - task_id: The identifier of the target task
            - transaction_id: The id of the transaction associated with the answer
    """
    LABEL = "AnsweredPickedMessage"

    def __init__(self, app_id: str, receiver_id: str, task_id: str, transaction_id: str, attributes: dict) -> None:
        attributes.update({
            "transactionId": transaction_id,
            "taskId": task_id,
        })
        super().__init__(app_id, receiver_id, self.LABEL, attributes)

    @staticmethod
    def from_repr(raw: dict) -> AnsweredPickedMessage:
        return AnsweredPickedMessage(
            raw["appId"],
            raw["receiverId"],
            raw["attributes"]["taskId"],
            raw["attributes"]["transactionId"],
            raw["attributes"]
        )

    @property
    def transaction_id(self) -> str:
        return self.attributes["transactionId"]

    @property
    def task_id(self) -> str:
        return self.attributes["taskId"]


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
