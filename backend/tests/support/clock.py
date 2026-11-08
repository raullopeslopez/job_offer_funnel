from datetime import date, datetime, time
from zoneinfo import ZoneInfo

# The time zone of the default settings: the user's.
ZONE = ZoneInfo("Europe/Madrid")


class FixedClock:
    def __init__(self, moment: datetime) -> None:
        self._moment = moment

    @classmethod
    def on(cls, day: date) -> FixedClock:
        """A clock at noon of `day`, for steps that only care about the date."""
        return cls(datetime.combine(day, time(12), ZONE))

    def today(self) -> date:
        return self._moment.date()

    def now(self) -> datetime:
        return self._moment
