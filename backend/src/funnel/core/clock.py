"""Injected clock: domain and services never read the system time directly."""

from datetime import date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo

from fastapi import Request

from funnel.core.config import Settings


class Clock(Protocol):
    def today(self) -> date: ...

    def now(self) -> datetime: ...


class SystemClock:
    """Time in the user's time zone, so day boundaries match theirs."""

    def __init__(self, timezone: str) -> None:
        self._zone = ZoneInfo(timezone)

    def today(self) -> date:
        return self.now().date()

    def now(self) -> datetime:
        return datetime.now(self._zone)


def get_clock(request: Request) -> Clock:
    settings: Settings = request.app.state.settings
    return SystemClock(settings.timezone)
