from __future__ import absolute_import, annotations

from typing import Optional


class Task:
    def __init__(self, creator: Optional[str] = None, when: Optional[str] = None, where: Optional[str] = None,
                 application_deadline: Optional[str] = None, max_people: Optional[str] = None,
                 name: Optional[str] = None, description: Optional[str] = None) -> None:
        self.creator = creator
        self.when = when
        self.where = where
        self.application_deadline = application_deadline
        self.max_people = max_people
        self.name = name
        self.description = description

    def to_repr(self) -> dict:
        return {
            "creator": self.creator,
            "when": self.when,
            "where": self.where,
            "application_deadline": self.application_deadline,
            "max_people": self.max_people,
            "name": self.name,
            "description": self.description
        }

    @staticmethod
    def from_repr(raw: dict) -> Task:
        return Task(
            raw["creator"],
            raw["when"],
            raw["where"],
            raw["application_deadline"],
            raw["max_people"],
            raw["name"],
            raw["description"],
        )

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Task):
            return False
        return self.name == o.name and self.description == o.description and self.where == o.where and \
               self.when == o.when and self.application_deadline == o.application_deadline and \
               self.max_people == o.max_people and self.creator == o.creator

    def recap_without_creator(self) -> str:
        return "*%s*\n%s\n:round_pushpin: *Where:* %s\n:calendar: *When:* %s\n" \
               ":alarm_clock: *Deadline:* %s\n:couple: *Guests:* %s" \
               % (self.name, self.description, self.where, self.when, self.application_deadline, self.max_people)
