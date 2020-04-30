import re
from datetime import datetime
from typing import Optional

from wenet.service_api.authentication_account import WeNetUserWithAccounts, TelegramAuthenticationAccount


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
