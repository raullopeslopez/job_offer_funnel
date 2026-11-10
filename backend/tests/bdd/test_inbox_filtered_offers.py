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
from funnel.modules.inbox.router import get_feed_client

pytestmark = pytest.mark.bdd

scenarios("inbox/filtered_offers.feature")

OFFERS_URL = "/api/v1/offers"
PROFILES_URL = "/api/v1/search-profiles"

Row = dict[str, str]


@dataclass
class ScenarioState:
    profiles: dict[str, str] = field(default_factory=dict)
    # What the fake sources answer: Remote OK's JSON and Greenhouse boards by board name.
    remoteok: list[Row] = field(default_factory=list)
    boards: dict[str, list[Row]] = field(default_factory=dict)
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


@pytest.fixture(autouse=True)
def fake_sources(client: TestClient, state: ScenarioState) -> Iterator[None]:
    """Remote OK and Greenhouse answer from the scenario: tests never reach the internet."""

    def answer(request: httpx2.Request) -> httpx2.Response:
        if request.url.host == "remoteok.com":
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
        board = request.url.path.strip("/").split("/")[2]  # /v1/boards/<board>/jobs
        jobs = [
            {"id": i, "title": r["title"], "content": r["description"], "absolute_url": r["url"]}
            for i, r in enumerate(state.boards[board])
        ]
        return httpx2.Response(200, json={"jobs": jobs, "meta": {"total": len(jobs)}})

    async def fake_client() -> AsyncIterator[httpx2.AsyncClient]:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(answer)) as fake:
            yield fake

    overrides = cast(FastAPI, client.app).dependency_overrides
    overrides[get_feed_client] = fake_client
    yield
    overrides.pop(get_feed_client, None)


def _rows(datatable: list[list[str]]) -> list[Row]:
    header, *rows = datatable
    return [dict(zip(header, values, strict=True)) for values in rows]


def _titles(text: str) -> list[str]:
    return re.findall(r'"([^"]*)"', text)


def _offers(client: TestClient, **params: str) -> list[dict[str, Any]]:
    response = client.get(OFFERS_URL, params=params)
    assert response.status_code == 200, response.text
    items: list[dict[str, Any]] = response.json()["items"]
    return items


def _offer_id(client: TestClient, title: str) -> str:
    offer_id: str = next(o["id"] for o in _offers(client) if o["title"] == title)
    return offer_id


def _ok(response: httpx2.Response, status: int = 201) -> dict[str, Any]:
    assert response.status_code == status, response.text
    body: dict[str, Any] = response.json() if response.content else {}
    return body


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
        body[key] = re.split(r"\s*,\s*", value)
    state.profiles[name] = _ok(client.post(PROFILES_URL, json=body))["id"]


@given("there are no search profiles")
def given_no_profiles(client: TestClient, state: ScenarioState) -> None:
    for profile_id in state.profiles.values():
        _ok(client.delete(f"{PROFILES_URL}/{profile_id}"), 204)
    state.profiles.clear()


@given(parsers.parse('the feed "remoteok" was imported with:'))
def given_feed_imported(
    client: TestClient, state: ScenarioState, datatable: list[list[str]]
) -> None:
    state.remoteok = _rows(datatable)
    _ok(client.post("/api/v1/feeds/remoteok/imports"))


@given(parsers.parse('the board of the watched company "{company}" was imported with:'))
def given_board_imported(
    client: TestClient, state: ScenarioState, company: str, datatable: list[list[str]]
) -> None:
    board = company.casefold()
    state.boards[board] = _rows(datatable)
    body = {"name": company, "ats": "greenhouse", "board": board}
    watched_id = _ok(client.post("/api/v1/watched-companies", json=body))["id"]
    _ok(client.post(f"/api/v1/watched-companies/{watched_id}/imports"))


@given(parsers.parse('an offer for "{company}" as "{title}"'))
def given_offer(client: TestClient, state: ScenarioState, company: str, title: str) -> None:
    body = {"url": f"https://jobs.example/{next(state.urls)}", "company": company, "title": title}
    _ok(client.post(OFFERS_URL, json=body))


@given(parsers.parse('I edit the profile "{name}" to have the titles "{titles}"'))
def given_profile_edited(client: TestClient, state: ScenarioState, name: str, titles: str) -> None:
    body = {"titles": re.split(r"\s*,\s*", titles)}
    _ok(client.patch(f"{PROFILES_URL}/{state.profiles[name]}", json=body), 200)


@given(parsers.parse('I delete the profile "{name}"'))
def given_profile_deleted(client: TestClient, state: ScenarioState, name: str) -> None:
    _ok(client.delete(f"{PROFILES_URL}/{state.profiles.pop(name)}"), 204)


@given(parsers.parse('I discarded the offer "{title}"'))
def given_discarded(client: TestClient, title: str) -> None:
    _ok(client.post(f"{OFFERS_URL}/{_offer_id(client, title)}/discard", json={}))


# --- When ---


@when(parsers.parse('I view the offer "{title}"'))
def when_view(client: TestClient, state: ScenarioState, title: str) -> None:
    state.offer = _ok(client.get(f"{OFFERS_URL}/{_offer_id(client, title)}"), 200)


@when(parsers.re(r"I list the pending offers that are (?P<which>filtered|not filtered)$"))
def when_list(client: TestClient, state: ScenarioState, which: str) -> None:
    filtered = "true" if which == "filtered" else "false"
    state.response = client.get(OFFERS_URL, params={"status": "pending", "filtered": filtered})


@when(parsers.re(r'I (?P<action>discard|promote) the offer "(?P<title>[^"]+)"$'))
def when_act(client: TestClient, state: ScenarioState, action: str, title: str) -> None:
    path = "discard" if action == "discard" else "promotion"
    state.response = client.post(f"{OFFERS_URL}/{_offer_id(client, title)}/{path}", json={})


# --- Then ---


@then(parsers.re(r"the offer is (?P<which>filtered|not filtered)$"))
def then_filtered(state: ScenarioState, which: str) -> None:
    assert state.offer is not None
    assert state.offer["filtered"] is (which == "filtered")


@then(parsers.parse("the offers are, in order: {titles}"))
def then_offers(state: ScenarioState, titles: str) -> None:
    body = _ok(state.last_response, 200)
    assert [item["title"] for item in body["items"]] == _titles(titles)


@then(parsers.parse('the offer "{title}" is "{status}"'))
def then_status(client: TestClient, state: ScenarioState, title: str, status: str) -> None:
    _ok(state.last_response)
    assert next(o for o in _offers(client) if o["title"] == title)["status"] == status
