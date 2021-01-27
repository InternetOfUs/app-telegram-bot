from __future__ import absolute_import, annotations


class ButtonPayload:
    """
    This class contains the payload of a button stored in redis
    Attributes:
        - payload: a dictionary containing arbitrary data
        - intent: the intent associated with the button
    """

    def __init__(self, payload: dict, intent: str) -> None:
        self.payload = payload
        self.intent = intent

    def to_repr(self) -> dict:
        return {
            "payload": self.payload,
            "intent": self.intent,
        }

    @staticmethod
    def from_repr(raw: dict) -> ButtonPayload:
        return ButtonPayload(
            raw["payload"],
            raw["intent"]
        )
