import re
from collections.abc import AsyncIterator, Callable, Iterator
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

scenarios("inbox/public_feeds.feature")

OFFERS_URL = "/api/v1/offers"
FEEDS_URL = "/api/v1/feeds"
FEED_HOSTS = {
    "remoteok.com": "remoteok",
    "remotive.com": "remotive",
    "himalayas.app": "himalayas",
    "jobicy.com": "jobicy",
}

Row = dict[str, str]


def _remoteok(rows: list[Row]) -> object:
    jobs = [
        {
            "position": r["title"],
            "company": r["company"],
            "description": r["description"],
            "url": r["url"],
        }
        for r in rows
    ]
    return [{"legal": "Link back to Remote OK and mention it as the source."}, *jobs]


def _remotive(rows: list[Row]) -> object:
    jobs = [
        {
            "title": r["title"],
            "company_name": r["company"],
            "description": r["description"],
            "url": r["url"],
        }
        for r in rows
    ]
    return {"jobs": jobs}


def _himalayas(rows: list[Row]) -> object:
    jobs = [
        {
            "title": r["title"],
            "companyName": r["company"],
            "description": r["description"],
            "applicationLink": r["url"],
        }
        for r in rows
    ]
    return {"jobs": jobs}


def _jobicy(rows: list[Row]) -> object:
    jobs = [
        {
            "jobTitle": r["title"],
            "companyName": r["company"],
            "jobDescription": r["description"],
            "url": r["url"],
        }
        for r in rows
    ]
    return {"jobs": jobs}


# The real shape of each feed's JSON, checked against the live APIs on 2026-11-08.
FEED_PAYLOADS: dict[str, Callable[[list[Row]], object]] = {
    "remoteok": _remoteok,
    "remotive": _remotive,
    "himalayas": _himalayas,
    "jobicy": _jobicy,
}


@dataclass
class ScenarioState:
    now: datetime | None = None
    profiles: dict[str, str] = field(default_factory=dict)
    published: dict[str, list[Row]] = field(default_factory=dict)
    unavailable: set[str] = field(default_factory=set)
    searched: dict[str, list[str]] = field(default_factory=dict)
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
def fake_feeds(client: TestClient, state: ScenarioState) -> Iterator[None]:
    """Every feed request is answered from the scenario: tests never reach the internet."""

    def answer(request: httpx2.Request) -> httpx2.Response:
        feed = FEED_HOSTS[request.url.host]
        if "q" in request.url.params:
            state.searched.setdefault(feed, []).append(request.url.params["q"])
        if feed in state.unavailable:
            return httpx2.Response(503)
        return httpx2.Response(200, json=FEED_PAYLOADS[feed](state.published.get(feed, [])))

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


def _local(text: str | None) -> str:
    return (
        ""
        if text is None
        else datetime.fromisoformat(text).astimezone(ZONE).strftime("%Y-%m-%d %H:%M")
    )


def _rows(datatable: list[list[str]]) -> list[Row]:
    header, *rows = datatable
    return [dict(zip(header, values, strict=True)) for values in rows]


def _import(client: TestClient, feed: str) -> httpx2.Response:
    return client.post(f"{FEEDS_URL}/{feed}/imports")


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


@given("there are no search profiles")
def given_no_profiles(client: TestClient, state: ScenarioState) -> None:
    for profile_id in state.profiles.values():
        response = client.delete(f"/api/v1/search-profiles/{profile_id}")
        assert response.status_code == 204, response.text
    state.profiles.clear()


@given(parsers.parse('the feed "{feed}" publishes:'))
def given_feed_publishes(state: ScenarioState, feed: str, datatable: list[list[str]]) -> None:
    state.published[feed] = _rows(datatable)


@given(parsers.parse('the feed "{feed}" publishes no offers'))
def given_feed_publishes_nothing(state: ScenarioState, feed: str) -> None:
    state.published[feed] = []


@given(parsers.parse('the feed "{feed}" is not available'))
def given_feed_down(state: ScenarioState, feed: str) -> None:
    state.unavailable.add(feed)


def _imported_at(client: TestClient, state: ScenarioState, feed: str, moment: str) -> None:
    assert state.now is not None, "the scenario must set the time first"
    _set_time(client, _moment(moment))
    response = _import(client, feed)
    assert response.status_code == 201, response.text
    _set_time(client, state.now)


@given(parsers.re(r'the feed "(?P<feed>[^"]+)" was imported at (?P<moment>[0-9: -]+)$'))
def given_feed_imported(client: TestClient, state: ScenarioState, feed: str, moment: str) -> None:
    state.published.setdefault(feed, [])
    _imported_at(client, state, feed, moment)


@given(parsers.parse('the feed "{feed}" was imported at {moment} with:'))
def given_feed_imported_with(
    client: TestClient, state: ScenarioState, feed: str, moment: str, datatable: list[list[str]]
) -> None:
    state.published[feed] = _rows(datatable)
    _imported_at(client, state, feed, moment)


@given(parsers.parse('I promoted the offer "{title}"'))
def given_promoted(client: TestClient, title: str) -> None:
    offer_id = _offer(client, title)["id"]
    response = client.post(f"{OFFERS_URL}/{offer_id}/promotion", json={})
    assert response.status_code == 201, response.text


@given(parsers.re(r'an offer for "(?P<company>[^"]+)" as "(?P<title>[^"]+)"$'))
def given_offer(client: TestClient, state: ScenarioState, company: str, title: str) -> None:
    _add_offer(client, state, company, title)


@given(parsers.parse('an offer for "{company}" as "{title}" that was discarded'))
def given_discarded_offer(
    client: TestClient, state: ScenarioState, company: str, title: str
) -> None:
    offer_id = _add_offer(client, state, company, title)
    response = client.post(f"{OFFERS_URL}/{offer_id}/discard", json={})
    assert response.status_code == 201, response.text


# --- When ---


@when(parsers.parse('I import the feed "{feed}"'))
def when_import(client: TestClient, state: ScenarioState, feed: str) -> None:
    state.response = _import(client, feed)


@when(parsers.parse('I add an offer for "{company}" as "{title}"'))
def when_add_offer(client: TestClient, state: ScenarioState, company: str, title: str) -> None:
    _add_offer(client, state, company, title)


@when("I list the feeds")
def when_list_feeds(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(FEEDS_URL)


# --- Then ---


@then(
    parsers.parse(
        "the import found {found:d} offers, {added:d} added, {filtered:d} filtered "
        "and {already:d} already in the inbox"
    )
)
def then_import_counts(
    state: ScenarioState, found: int, added: int, filtered: int, already: int
) -> None:
    response = state.last_response
    assert response.status_code == 201, response.text
    body = response.json()
    counts = (body["found"], body["added"], body["filtered"], body["already_in_inbox"])
    assert counts == (found, added, filtered, already)


@then(parsers.parse('the feed "{feed}" was searched for: {queries}'))
def then_searched_for(state: ScenarioState, feed: str, queries: str) -> None:
    assert state.searched.get(feed, []) == re.findall(r'"([^"]*)"', queries)


@then(parsers.parse('the feed "{feed}" was not searched'))
def then_not_searched(state: ScenarioState, feed: str) -> None:
    assert feed not in state.searched


@then(parsers.parse("the pending offers are: {titles}"))
def then_pending_offers(client: TestClient, titles: str) -> None:
    response = client.get(OFFERS_URL, params={"status": "pending"})
    assert response.status_code == 200, response.text
    expected = re.findall(r'"([^"]*)"', titles)
    assert [item["title"] for item in response.json()["items"]] == expected


@then(parsers.parse('the offer "{title}" links to "{url}" and comes from the feed "{feed}"'))
def then_offer_source(client: TestClient, title: str, url: str, feed: str) -> None:
    offer = _offer(client, title)
    assert (offer["url"], offer["feed"]) == (url, feed)


@then(parsers.parse('the offer "{title}" comes from no feed'))
def then_offer_without_feed(client: TestClient, title: str) -> None:
    assert _offer(client, title)["feed"] is None


@then(parsers.re(r'the offer "(?P<title>[^"]+)" is "(?P<status>[^"]+)"$'))
def then_offer_status(client: TestClient, title: str, status: str) -> None:
    assert _offer(client, title)["status"] == status


@then(parsers.parse('the offer "{title}" is "{status}" with reason "{reason}"'))
def then_offer_status_reason(client: TestClient, title: str, status: str, reason: str) -> None:
    offer = _offer(client, title)
    assert (offer["status"], offer["discard_reason"]) == (status, reason)


@then(parsers.parse("it is rejected because the feed was imported too recently, until {moment}"))
def then_cooldown(state: ScenarioState, moment: str) -> None:
    assert state.now is not None
    _assert_problem(state, 429, "feed-cooldown")
    wait = (_moment(moment) - state.now).total_seconds()
    assert int(state.last_response.headers["Retry-After"]) == int(wait)


REJECTIONS = {
    "the feed is not available": (502, "feed-unavailable"),
    "the feed does not exist": (404, "not-found"),
}


@then(
    parsers.re(
        r"it is rejected because (?P<reason>the feed is not available|the feed does not exist)$"
    )
)
def then_rejected(state: ScenarioState, reason: str) -> None:
    _assert_problem(state, *REJECTIONS[reason])


@then(parsers.parse('the feed "{feed}" has never been imported'))
def then_never_imported(client: TestClient, feed: str) -> None:
    response = client.get(FEEDS_URL)
    assert response.status_code == 200, response.text
    feeds = {item["feed"]: item for item in response.json()}
    assert feeds[feed]["last_imported_at"] is None


@then("the feeds are:")
def then_feeds_are(state: ScenarioState, datatable: list[list[str]]) -> None:
    response = state.last_response
    assert response.status_code == 200, response.text
    actual = [
        {
            "feed": item["feed"],
            "last_imported_at": _local(item["last_imported_at"]),
            "next_import_at": _local(item["next_import_at"]),
        }
        for item in response.json()
    ]
    assert actual == _rows(datatable)
