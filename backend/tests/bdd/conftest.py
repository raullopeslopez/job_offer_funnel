"""Steps shared by several features."""

from datetime import date
from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers
from support.clock import FixedClock

from funnel.core.clock import get_clock


@given(parsers.parse("today is {day}"))
def given_today_is(client: TestClient, day: str) -> None:
    clock = FixedClock.on(date.fromisoformat(day))
    cast(FastAPI, client.app).dependency_overrides[get_clock] = lambda: clock
