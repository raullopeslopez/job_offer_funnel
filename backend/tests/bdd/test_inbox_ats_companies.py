import re
from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from itertools import count
from typing import Any, cast
from uuid import uuid7

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when
from support.clock import ZONE, FixedClock

from funnel.core.clock import get_clock
from funnel.modules.inbox.router import get_feed_client

pytestmark = pytest.mark.bdd

scenarios("inbox/ats_companies.feature")

OFFERS_URL = "/api/v1/offers"
WATCHED_URL = "/api/v1/watched-companies"
ATS_HOSTS = {
    "boards-api.greenhouse.io": "greenhouse",
    "api.lever.co": "lever",
    "api.ashbyhq.com": "ashby",
}

Row = dict[str, str]


def _greenhouse(rows: list[Row]) -> object:
    # The description comes as escaped HTML.
    jobs = [
        {"id": index, "title": r["title"], "content": r["description"], "absolute_url": r["url"]}
        for index, r in enumerate(rows)
    ]
    return {"jobs": jobs, "meta": {"total": len(jobs)}}


def _lever(rows: list[Row]) -> object:
    return [
        {
            "id": str(index),
            "text": r["title"],
            "descriptionPlain": r["description"],
            "hostedUrl": r["url"],
        }
        for index, r in enumerate(rows)
    ]


def _ashby(rows: list[Row]) -> object:
    jobs = [
        {
            "id": str(index),
            "title": r["title"],
            "descriptionPlain": r["description"],
            "jobUrl": r["url"],
            "isListed": True,
        }
        for index, r in enumerate(rows)
    ]
    return {"apiVersion": "1", "jobs": jobs}


# The real shape of each ATS board's JSON, checked against the live APIs on 2026-11-08.
ATS_PAYLOADS: dict[str, Callable[[list[Row]], object]] = {
    "greenhouse": _greenhouse,
    "lever": _lever,
    "ashby": _ashby,
}


@dataclass(frozen=True)
class Watched:
    id: str
    ats: str
    board: str


@dataclass
class ScenarioState:
    now: datetime | None = None
    profiles: dict[str, str] = field(default_factory=dict)
    watched: dict[str, Watched] = field(default_factory=dict)
    # Keyed by (ats, board), as the ATS sees the request.
    published: dict[tuple[str, str], list[Row]] = field(default_factory=dict)
    unavailable: set[tuple[str, str]] = field(default_factory=set)
    response: httpx2.Response | None = None
    urls: count[int] = field(default_factory=count)

    @property
    def last_response(self) -> httpx2.Response:
        assert self.response is not None, "no request was made in this scenario"
        return self.response

    def board(self, company: str) -> tuple[str, str]:
        watched = self.watched[company]
        return watched.ats, watched.board


@pytest.fixture
def state() -> ScenarioState:
    return ScenarioState()


@pytest.fixture(autouse=True)
def fake_boards(client: TestClient, state: ScenarioState) -> Iterator[None]:
    """Every ATS request is answered from the scenario: tests never reach the internet."""

    def answer(request: httpx2.Request) -> httpx2.Response:
        ats = ATS_HOSTS[request.url.host]
        # The board is the last path segment, except on Greenhouse (/v1/boards/<board>/jobs).
        segments = request.url.path.strip("/").split("/")
        board = segments[2] if ats == "greenhouse" else segments[-1]
        if (ats, board) in state.unavailable:
            return httpx2.Response(503)
        if (ats, board) not in state.published:
            return httpx2.Response(404)
        return httpx2.Response(200, json=ATS_PAYLOADS[ats](state.published[ats, board]))

    async def fake_client() -> AsyncIterator[httpx2.AsyncClient]:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(answer)) as fake:
            yield fake

    overrides = cast(FastAPI, client.app).dependency_overrides
    overrides[get_feed_client] = fake_client
    yield
    overrides.pop(get_feed_client, None)


def _set_time(client: TestClient, moment: datetime) -> None:
    clock = FixedClock(moment)
    cast(FastAPI, client.app).dependency_overrides[get_clock] = lambda: clock


def _moment(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=ZONE)


def _rows(datatable: list[list[str]]) -> list[Row]:
    header, *rows = datatable
    return [dict(zip(header, values, strict=True)) for values in rows]


def _watch(
    client: TestClient, state: ScenarioState, name: str, ats: str, board: str
) -> httpx2.Response:
    response = client.post(WATCHED_URL, json={"name": name, "ats": ats, "board": board})
    if response.status_code == 201:
        body = response.json()
        state.watched[body["name"]] = Watched(body["id"], body["ats"], body["board"])
    return response


def _import(
    client: TestClient, state: ScenarioState, company: str, profile: str
) -> httpx2.Response:
    watched = state.watched.get(company)
    watched_id = watched.id if watched is not None else str(uuid7())
    profile_id = state.profiles.get(profile, str(uuid7()))
    return client.post(f"{WATCHED_URL}/{watched_id}/imports", json={"profile_id": profile_id})


def _import_ok(client: TestClient, state: ScenarioState, company: str) -> None:
    response = _import(client, state, company, "Backend")
    assert response.status_code == 201, response.text


def _offer(client: TestClient, title: str) -> dict[str, Any]:
    response = client.get(OFFERS_URL)
    assert response.status_code == 200, response.text
    offers: list[dict[str, Any]] = response.json()["items"]
    return next(offer for offer in offers if offer["title"] == title)


def _add_offer(client: TestClient, state: ScenarioState, company: str, title: str) -> str:
    body = {"url": f"https://jobs.example/{next(state.urls)}", "company": company, "title": title}
    response = client.post(OFFERS_URL, json=body)
    assert response.status_code == 201, response.text
    offer_id: str = response.json()["id"]
    return offer_id


def _watched_companies(client: TestClient) -> list[dict[str, Any]]:
    response = client.get(WATCHED_URL)
    assert response.status_code == 200, response.text
    companies: list[dict[str, Any]] = response.json()
    return companies


def _assert_problem(state: ScenarioState, status: int, slug: str) -> None:
    response = state.last_response
    assert (response.status_code, response.json()["type"]) == (status, f"/problems/{slug}")


# --- Given ---


@given(parsers.parse("the time is {moment}"))
def given_time(client: TestClient, state: ScenarioState, moment: str) -> None:
    state.now = _moment(moment)
    _set_time(client, state.now)


@given(parsers.parse('a search profile named "{name}" with:'))
def given_profile(
    client: TestClient, state: ScenarioState, name: str, datatable: list[list[str]]
) -> None:
    body: dict[str, Any] = {"name": name}
    for key, value in datatable:
        body[key] = re.split(r"\s*,\s*", value)
    response = client.post("/api/v1/search-profiles", json=body)
    assert response.status_code == 201, response.text
    state.profiles[name] = response.json()["id"]


@given(parsers.parse('the company "{name}" is watched on "{ats}" with board "{board}"'))
def given_watched(
    client: TestClient, state: ScenarioState, name: str, ats: str, board: str
) -> None:
    response = _watch(client, state, name, ats, board)
    assert response.status_code == 201, response.text


@given(parsers.parse('the board of "{company}" publishes:'))
def given_board_publishes(state: ScenarioState, company: str, datatable: list[list[str]]) -> None:
    state.published[state.board(company)] = _rows(datatable)


@given(parsers.parse('the board of "{company}" publishes no offers'))
def given_board_publishes_nothing(state: ScenarioState, company: str) -> None:
    state.published[state.board(company)] = []


@given(parsers.parse('the board of "{company}" is not available'))
def given_board_down(state: ScenarioState, company: str) -> None:
    state.unavailable.add(state.board(company))


@given(parsers.parse('the board of "{company}" was imported with:'))
def given_board_imported_with(
    client: TestClient, state: ScenarioState, company: str, datatable: list[list[str]]
) -> None:
    state.published[state.board(company)] = _rows(datatable)
    _import_ok(client, state, company)


@given(parsers.parse('the board of "{company}" was imported at {moment}'))
def given_board_imported_at(
    client: TestClient, state: ScenarioState, company: str, moment: str
) -> None:
    assert state.now is not None, "the scenario must set the time first"
    state.published.setdefault(state.board(company), [])
    _set_time(client, _moment(moment))
    _import_ok(client, state, company)
    _set_time(client, state.now)


@given(parsers.parse('I promoted the offer "{title}"'))
def given_promoted(client: TestClient, title: str) -> None:
    offer_id = _offer(client, title)["id"]
    response = client.post(f"{OFFERS_URL}/{offer_id}/promotion", json={})
    assert response.status_code == 201, response.text


@given(parsers.parse('an offer for "{company}" as "{title}" that was discarded'))
def given_discarded_offer(
    client: TestClient, state: ScenarioState, company: str, title: str
) -> None:
    offer_id = _add_offer(client, state, company, title)
    response = client.post(f"{OFFERS_URL}/{offer_id}/discard", json={})
    assert response.status_code == 201, response.text


# --- When ---


@when(
    parsers.re(
        r'I watch the company "(?P<name>[^"]*)" on "(?P<ats>[^"]*)" with board "(?P<board>[^"]*)"$'
    )
)
def when_watch(client: TestClient, state: ScenarioState, name: str, ats: str, board: str) -> None:
    state.response = _watch(client, state, name, ats, board)


@when("I list the watched companies")
def when_list(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(WATCHED_URL)


@when(parsers.parse('I stop watching the company "{name}"'))
def when_unwatch(client: TestClient, state: ScenarioState, name: str) -> None:
    watched = state.watched.get(name)
    watched_id = watched.id if watched is not None else str(uuid7())
    state.response = client.delete(f"{WATCHED_URL}/{watched_id}")


@when(parsers.parse('I import the watched company "{company}" for the profile "{profile}"'))
def when_import(client: TestClient, state: ScenarioState, company: str, profile: str) -> None:
    state.response = _import(client, state, company, profile)


@when(parsers.parse('I add an offer for "{company}" as "{title}"'))
def when_add_offer(client: TestClient, state: ScenarioState, company: str, title: str) -> None:
    _add_offer(client, state, company, title)


# --- Then ---


@then(parsers.parse('the company "{name}" is watched on "{ats}" with board "{board}"'))
def then_watched(client: TestClient, name: str, ats: str, board: str) -> None:
    companies = [(c["name"], c["ats"], c["board"]) for c in _watched_companies(client)]
    assert (name, ats, board) in companies


@then(parsers.parse('the company "{name}" is not watched'))
def then_not_watched(client: TestClient, state: ScenarioState, name: str) -> None:
    assert state.last_response.status_code == 204, state.last_response.text
    assert name not in [c["name"] for c in _watched_companies(client)]


@then("the watched companies are:")
def then_watched_companies(state: ScenarioState, datatable: list[list[str]]) -> None:
    response = state.last_response
    assert response.status_code == 200, response.text
    actual = [{"name": c["name"], "ats": c["ats"], "board": c["board"]} for c in response.json()]
    assert actual == _rows(datatable)


@then(
    parsers.parse(
        "the import found {found:d} offers, {matching:d} matching, {added:d} added "
        "and {already:d} already in the inbox"
    )
)
def then_import_counts(
    state: ScenarioState, found: int, matching: int, added: int, already: int
) -> None:
    response = state.last_response
    assert response.status_code == 201, response.text
    body = response.json()
    counts = (body["found"], body["matching"], body["added"], body["already_in_inbox"])
    assert counts == (found, matching, added, already)


@then(parsers.parse("the pending offers are: {titles}"))
def then_pending_offers(client: TestClient, titles: str) -> None:
    response = client.get(OFFERS_URL, params={"status": "pending"})
    assert response.status_code == 200, response.text
    expected = re.findall(r'"([^"]*)"', titles)
    assert [item["title"] for item in response.json()["items"]] == expected


@then(
    parsers.parse(
        'the offer "{title}" is for "{company}", links to "{url}" '
        'and comes from the watched company "{watched}"'
    )
)
def then_offer_source(client: TestClient, title: str, company: str, url: str, watched: str) -> None:
    offer = _offer(client, title)
    assert (offer["company"], offer["url"], offer["watched_company_name"]) == (
        company,
        url,
        watched,
    )
    assert offer["watched_company_id"] is not None


@then(parsers.parse('the offer "{title}" comes from no watched company'))
def then_offer_without_source(client: TestClient, title: str) -> None:
    offer = _offer(client, title)
    assert (offer["watched_company_id"], offer["watched_company_name"]) == (None, None)


@then(parsers.parse('the offer "{title}" is "{status}" and comes from no watched company'))
def then_offer_status_without_source(client: TestClient, title: str, status: str) -> None:
    offer = _offer(client, title)
    assert (offer["status"], offer["watched_company_id"]) == (status, None)


@then(parsers.re(r'the offer "(?P<title>[^"]+)" is "(?P<status>[^"]+)"$'))
def then_offer_status(client: TestClient, title: str, status: str) -> None:
    assert _offer(client, title)["status"] == status


@then(parsers.parse('the offer "{title}" is "{status}" with reason "{reason}"'))
def then_offer_status_reason(client: TestClient, title: str, status: str, reason: str) -> None:
    offer = _offer(client, title)
    assert (offer["status"], offer["discard_reason"]) == (status, reason)


@then("it is rejected as invalid")
def then_invalid(state: ScenarioState) -> None:
    _assert_problem(state, 422, "validation-error")


REJECTIONS = {
    "the company is already watched": (409, "already-exists"),
    "the board is not available": (502, "board-unavailable"),
    "the watched company does not exist": (404, "not-found"),
    "the search profile does not exist": (422, "unknown-search-profile"),
}


@then(parsers.re(r"it is rejected because (?P<reason>.+)$"))
def then_rejected(state: ScenarioState, reason: str) -> None:
    _assert_problem(state, *REJECTIONS[reason])
