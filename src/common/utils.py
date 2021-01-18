import re
from datetime import datetime
from typing import Optional

from wenet.common.model.task.task import Task
from wenet.common.model.user.authentication_account import WeNetUserWithAccounts, TelegramAuthenticationAccount


class Utils:
    @staticmethod
    def parse_datetime(text: str) -> Optional[datetime]:
        match = re.match("(?P<year>[0-9]{4}) (?P<month>[0-9]{2}) (?P<day>[0-9]{2}) (?P<hour>[0-9]{2}) "
                         "(?P<minutes>[0-9]{2})", text)
        if match:
            try:
                timestamp = datetime(int(match.group("year")), int(match.group("month")), int(match.group("day")),
                                     int(match.group("hour")), int(match.group("minutes")))
                return timestamp
            except ValueError:
                return None
        return None

    @staticmethod
    def extract_telegram_account(user: WeNetUserWithAccounts) -> Optional[TelegramAuthenticationAccount]:
        for account in user.accounts:
            if isinstance(account, TelegramAuthenticationAccount):
                return account
        return None

    @staticmethod
    def task_recap_complete(task: Task, creator_name: str) -> str:
        return "*%s*\n%s\n:round_pushpin: *Where:* %s\n:calendar: *When:* %s\n" \
               ":alarm_clock: *Deadline:* %s\n:couple: *Guests:* %s\n:girl: *Creator:* %s" \
               % (task.goal.name, task.goal.description, task.attributes["where"],
                  datetime.fromtimestamp(task.attributes["startTs"]).strftime("%d/%m/%Y, %H:%M:%S"),
                  datetime.fromtimestamp(task.attributes["deadlineTs"]).strftime("%d/%m/%Y, %H:%M:%S"),
                  task.attributes["maxPeople"], creator_name.replace('_', ''))

    @staticmethod
    def task_recap_without_creator(task: Task) -> str:
        return "*%s*\n%s\n:round_pushpin: *Where:* %s\n:calendar: *When:* %s\n" \
               ":alarm_clock: *Deadline:* %s\n:couple: *Guests:* %s" \
               % (task.goal.name, task.goal.description, task.attributes["where"],
                  datetime.fromtimestamp(task.attributes["startTs"]).strftime("%d/%m/%Y, %H:%M:%S"),
                  datetime.fromtimestamp(task.attributes["deadlineTs"]).strftime("%d/%m/%Y, %H:%M:%S"),
                  task.attributes["maxPeople"])
