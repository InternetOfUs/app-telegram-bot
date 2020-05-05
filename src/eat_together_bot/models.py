from __future__ import absolute_import, annotations

from datetime import datetime, timedelta
from typing import Optional


class Task:
    def __init__(self, id: str, creator: str, when: Optional[datetime] = None,
                 where: Optional[str] = None, application_deadline: Optional[datetime] = None,
                 max_people: Optional[str] = None, name: Optional[str] = None,
                 description: Optional[str] = None) -> None:
        self.creator = creator
        self.when = when
        self.where = where
        self.application_deadline = application_deadline
        self.max_people = max_people
        self.name = name
        self.description = description
        self.id = id

    def to_repr(self) -> dict:
        return {
            "creator": self.creator,
            "when": self.when.timestamp() if self.when is not None else None,
            "where": self.where,
            "application_deadline": self.application_deadline.timestamp()
            if self.application_deadline is not None else None,
            "max_people": self.max_people,
            "name": self.name,
            "description": self.description,
            "id": self.id
        }

    @staticmethod
    def from_repr(raw: dict) -> Task:
        return Task(
            raw["id"],
            raw["creator"],
            datetime.fromtimestamp(raw["when"]) if raw["when"] is not None else None,
            raw["where"],
            datetime.fromtimestamp(raw["application_deadline"])
            if raw["application_deadline"] is not None else None,
            raw["max_people"],
            raw["name"],
            raw["description"],
        )

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Task):
            return False
        return self.name == o.name and self.description == o.description and self.where == o.where and \
               self.when == o.when and self.application_deadline == o.application_deadline and \
               self.max_people == o.max_people and self.creator == o.creator and self.id == o.id

    def recap_without_creator(self) -> str:
        return "*%s*\n%s\n:round_pushpin: *Where:* %s\n:calendar: *When:* %s\n" \
               ":alarm_clock: *Deadline:* %s\n:couple: *Guests:* %s" \
               % (self.name, self.description, self.where, self.when.strftime("%d/%m/%Y, %H:%M:%S"),
                  self.application_deadline.strftime("%d/%m/%Y, %H:%M:%S"), self.max_people)

    def recap_complete(self) -> str:
        return "*%s*\n%s\n:round_pushpin: *Where:* %s\n:calendar: *When:* %s\n" \
               ":alarm_clock: *Deadline:* %s\n:couple: *Guests:* %s\n:girl: *Creator:* %s" \
               % (self.name, self.description, self.where, self.when.strftime("%d/%m/%Y, %H:%M:%S"),
                  self.application_deadline.strftime("%d/%m/%Y, %H:%M:%S"), self.max_people,
                  self.creator.replace('_', ''))

    @staticmethod
    def from_service_api_task_repr(raw: dict) -> Task:
        # TODO some values are just mocks! When service API will change, this function must change too!
        return Task(
            raw["taskId"],
            raw["requesterId"],
            datetime.fromtimestamp(raw["startTs"]),
            "Trento",
            datetime.fromtimestamp(raw["deadlineTs"]),
            "100",
            raw["goal"]["name"],
            raw["goal"]["description"]
        )

    def to_service_api_repr(self, app_id: str) -> dict:
        end_ts = self.when + timedelta(hours=1)
        return {
            "taskId": self.id,
            "_creationTs": int(datetime.now().timestamp()),
            "_lastUpdateTs": int(datetime.now().timestamp()),
            "taskTypeId": "task_type_id",
            "requesterId": str(self.creator),
            "appId": app_id,
            "goal": {
                "name": self.name,
                "description": self.description
            },
            "startTs": int(self.when.timestamp()),
            "endTs": int(end_ts.timestamp()),
            "deadlineTs": int(self.application_deadline.timestamp()),
            "norms": [],
            "attributes": []
        }
