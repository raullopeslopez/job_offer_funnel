import re
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from itertools import count
from typing import Any, cast

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when
from support.clock import ZONE, FixedClock

from funnel.core.clock import get_clock
from funnel.modules.discovery.domain import WorkMode
from funnel.modules.inbox.domain import OfferReaderError, OfferText, Reading
from funnel.modules.inbox.router import get_feed_client, get_offer_reader

pytestmark = pytest.mark.bdd

scenarios("inbox/offer_readings.feature")

OFFERS_URL = "/api/v1/offers"
READINGS_URL = f"{OFFERS_URL}/readings"
PROFILES_URL = "/api/v1/search-profiles"
LIST_FIELDS = frozenset({"titles", "keywords", "excluded_keywords", "work_modes"})
YES_NO = {"yes": True, "no": False, "": None}

Row = dict[str, str]


@dataclass
class ScenarioState:
    profiles: dict[str, str] = field(default_factory=dict)
    remoteok: list[Row] = field(default_factory=list)
    remoteok_id: str | None = None
    # What the fake offer reader answers, by offer title, and the companies it fails on.
    answers: dict[str, Reading] = field(default_factory=dict)
    failing: set[str] = field(default_factory=set)
    has_reader: bool = True
    offer: dict[str, Any] | None = None
    response: httpx2.Response | None = None
    urls: count[int] = field(default_factory=count)

    @property
    def last_response(self) -> httpx2.Response:
        assert self.response is not None, "no request was made in this scenario"
        return self.response


@pytest.fixture
def state() -> ScenarioState:
    return ScenarioState()


class FakeOfferReader:
    """Answers what the scenario says; a description it knows nothing about says nothing."""

    def __init__(self, state: ScenarioState) -> None:
        self._state = state

    async def read(self, offer: OfferText, _location: str | None) -> Reading:
        if offer.company in self._state.failing:
            raise OfferReaderError("the reader is down")
        return self._state.answers.get(offer.title, Reading())


@pytest.fixture(autouse=True)
def fake_sources(client: TestClient, state: ScenarioState) -> Iterator[None]:
    """Remote OK and the offer reader answer from the scenario: tests never reach the
    internet."""

    def answer(_request: httpx2.Request) -> httpx2.Response:
        jobs = [
            {
                "position": r["title"],
                "company": r["company"],
                "description": r["description"],
                "url": r["url"],
            }
            for r in state.remoteok
        ]
        return httpx2.Response(200, json=[{"legal": "Link back to Remote OK."}, *jobs])

    async def fake_client() -> AsyncIterator[httpx2.AsyncClient]:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(answer)) as fake:
            yield fake

    overrides = cast(FastAPI, client.app).dependency_overrides
    overrides[get_feed_client] = fake_client
    overrides[get_offer_reader] = lambda: FakeOfferReader(state) if state.has_reader else None
    yield
    overrides.pop(get_feed_client, None)
    overrides.pop(get_offer_reader, None)


def _rows(datatable: list[list[str]]) -> list[Row]:
    header, *rows = datatable
    return [dict(zip(header, values, strict=True)) for values in rows]


def _words(text: str) -> list[str]:
    return re.split(r"\s*,\s*", text)


def _offers(client: TestClient) -> list[dict[str, Any]]:
    response = client.get(OFFERS_URL, params={"limit": "100"})
    assert response.status_code == 200, response.text
    items: list[dict[str, Any]] = response.json()["items"]
    return items


def _offer(client: TestClient, title: str) -> dict[str, Any]:
    return next(offer for offer in _offers(client) if offer["title"] == title)


def _ok(response: httpx2.Response, status: int = 201) -> dict[str, Any]:
    assert response.status_code == status, response.text
    body: dict[str, Any] = response.json() if response.content else {}
    return body


def _answers(row: Row) -> dict[str, Any]:
    """A table row as the API shows a reading: only the columns the scenario gives."""
    answers: dict[str, Any] = {}
    for column, value in row.items():
        if column in {"admits_location", "stable"}:
            answers[column] = YES_NO[value]
        else:
            answers[column] = value or None
    return answers


def _reading(answers: dict[str, Any]) -> Reading:
    work_mode = answers.pop("work_mode", None)
    return Reading(work_mode=None if work_mode is None else WorkMode(work_mode), **answers)


def _import(client: TestClient, state: ScenarioState, rows: list[Row]) -> None:
    state.remoteok = rows
    _ok(client.post(f"/api/v1/job-boards/{state.remoteok_id}/imports"))


# --- Given ---


@given(parsers.parse("the time is {moment}"))
def given_time(client: TestClient, moment: str) -> None:
    clock = FixedClock(datetime.fromisoformat(moment).replace(tzinfo=ZONE))
    cast(FastAPI, client.app).dependency_overrides[get_clock] = lambda: clock


@given(parsers.parse('a search profile named "{name}" with:'))
def given_profile(
    client: TestClient, state: ScenarioState, name: str, datatable: list[list[str]]
) -> None:
    body: dict[str, Any] = {"name": name}
    for key, value in datatable:
        body[key] = _words(value) if key in LIST_FIELDS else value
    state.profiles[name] = _ok(client.post(PROFILES_URL, json=body))["id"]


@given(parsers.parse('a job board named "Remote OK" imported from the feed "remoteok"'))
def given_remoteok_job_board(client: TestClient, state: ScenarioState) -> None:
    body = {
        "name": "Remote OK",
        "search_url_template": "https://remoteok.com/?q={query}",
        "syntax": "keywords",
        "import_method": "api",
        "feed": "remoteok",
    }
    state.remoteok_id = _ok(client.post("/api/v1/job-boards", json=body))["id"]


@given(parsers.parse('the job board "Remote OK" was imported with:'))
def given_job_board_imported(
    client: TestClient, state: ScenarioState, datatable: list[list[str]]
) -> None:
    _import(client, state, _rows(datatable))


@given(parsers.parse('the job board "Remote OK" was imported with {number:d} offers as "{title}"'))
def given_many_imported(client: TestClient, state: ScenarioState, number: int, title: str) -> None:
    rows = [
        {
            "title": title,
            "company": f"Company {index}",
            "description": "Python services.",
            "url": f"https://remoteok.com/{index}",
        }
        for index in range(number)
    ]
    _import(client, state, rows)


@given(parsers.parse('an offer for "{company}" as "{title}"'))
def given_offer(client: TestClient, state: ScenarioState, company: str, title: str) -> None:
    body = {"url": f"https://jobs.example/{next(state.urls)}", "company": company, "title": title}
    _ok(client.post(OFFERS_URL, json=body))


@given(parsers.parse('the offer reader answers for "{title}":'))
def given_answers(state: ScenarioState, title: str, datatable: list[list[str]]) -> None:
    (row,) = _rows(datatable)
    state.answers[title] = _reading(_answers(row))


@given(parsers.parse('the offer reader fails on the offer of "{company}"'))
def given_reader_fails(state: ScenarioState, company: str) -> None:
    state.failing.add(company)


@given("there is no offer reader")
def given_no_reader(state: ScenarioState) -> None:
    state.has_reader = False


@given(parsers.re(r'I edit the profile "(?P<name>[^"]+)" to have (?P<change>.+)$'))
def given_profile_edited(client: TestClient, state: ScenarioState, name: str, change: str) -> None:
    body: dict[str, Any] = {}
    if "no location" in change:
        body["location"] = None
    if "no work modes" in change:
        body["work_modes"] = []
    if quoted := re.search(r'the (location|work modes) "([^"]+)"', change):
        body |= (
            {"location": quoted[2]}
            if quoted[1] == "location"
            else {"work_modes": _words(quoted[2])}
        )
    _ok(client.patch(f"{PROFILES_URL}/{state.profiles[name]}", json=body), 200)


@given(parsers.re(r'I (?P<action>discarded|promoted) the offer "(?P<title>[^"]+)"$'))
def given_acted(client: TestClient, action: str, title: str) -> None:
    path = "discard" if action == "discarded" else "promotion"
    _ok(client.post(f"{OFFERS_URL}/{_offer(client, title)['id']}/{path}", json={}))


# --- When ---


@given("I read the offers")
@when("I read the offers")
def when_read(client: TestClient, state: ScenarioState) -> None:
    state.response = client.post(READINGS_URL)


@when(parsers.parse('I view the offer "{title}"'))
def when_view(client: TestClient, state: ScenarioState, title: str) -> None:
    state.offer = _ok(client.get(f"{OFFERS_URL}/{_offer(client, title)['id']}"), 200)


# --- Then ---


@then(
    parsers.parse(
        "the reading read {read:d} offers, failed on {failed:d} and left {left:d} to read"
    )
)
def then_batch(state: ScenarioState, read: int, failed: int, left: int) -> None:
    assert _ok(state.last_response) == {"read": read, "failed": failed, "left": left}


@then(parsers.re(r'the reading of "(?P<title>[^"]+)"(?: for "(?P<location>[^"]+)")? says:$'))
def then_reading(
    client: TestClient, title: str, location: str | None, datatable: list[list[str]]
) -> None:
    (row,) = _rows(datatable)
    (reading,) = [r for r in _offer(client, title)["readings"] if r["location"] == location]
    expected = _answers(row)
    assert {column: reading[column] for column in expected} == expected


@then(parsers.re(r'the offer "(?P<title>[^"]+)" has no readings$'))
def then_no_readings(client: TestClient, title: str) -> None:
    assert _offer(client, title)["readings"] == []


@then(parsers.re(r'the offer "(?P<title>[^"]+)" has no reading for "(?P<location>[^"]+)"$'))
def then_no_reading_for(client: TestClient, title: str, location: str) -> None:
    assert location not in [r["location"] for r in _offer(client, title)["readings"]]


@then(parsers.re(r"the offer is (?P<which>filtered|not filtered)$"))
def then_filtered(state: ScenarioState, which: str) -> None:
    assert state.offer is not None
    assert state.offer["filtered"] is (which == "filtered")
    # The filter reason never contradicts it (specs/inbox/filter_reasons.feature).
    reason = state.offer["filter_reason"]
    failed = reason is not None and any(r["result"] == "failed" for r in reason["rules"])
    assert failed is state.offer["filtered"]


@then("it is rejected because the offer reader is not available")
def then_unavailable(state: ScenarioState) -> None:
    assert state.last_response.status_code == 503, state.last_response.text
    assert state.last_response.json()["type"] == "/problems/offer-reader-unavailable"
