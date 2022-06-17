from __future__ import absolute_import, annotations
from wenet.model.callback_message.event import Event


class WeNetAuthenticationEvent(Event):
    """
    Event used during the authentication of an user

    Attributes:
        - type: the type of event (only 'WeNetAuthenticationEvent' is available)
        - external_id: the ID of the user on an external platform, e.g. Telegram
        - code: the code of the authentication process
    """
    TYPE = "weNetAuthentication"

    def __init__(self, external_id: str, code: str) -> None:
        super().__init__(self.TYPE)
        self.external_id = external_id
        self.code = code

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, WeNetAuthenticationEvent):
            return False
        return self.external_id == o.external_id and self.code == o.code and self.event_type == o.event_type

    def to_repr(self) -> dict:
        return {
            "type": self.event_type,
            "externalId": self.external_id,
            "code": self.code,
        }

    @staticmethod
    def from_repr(raw: dict) -> WeNetAuthenticationEvent:
        return WeNetAuthenticationEvent(
            raw["externalId"],
            raw["code"]
        )


class CreationError(ValueError):

    def __init__(self, http_status_code: int, server_response: str) -> None:
        super().__init__(f"Request has return a code [{http_status_code}] with content [{server_response}]")
        self.http_status_code = http_status_code
        self.server_response = server_response
        self.message = f"Request has return a code [{http_status_code}] with content [{server_response}]"
