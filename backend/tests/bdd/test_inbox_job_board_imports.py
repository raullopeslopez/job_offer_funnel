import re
from collections import defaultdict
from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from itertools import count
from typing import Any, cast
from uuid import uuid7
from xml.sax.saxutils import escape

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when
from support.clock import ZONE, FixedClock

from funnel.core.clock import get_clock
from funnel.modules.inbox.router import get_feed_client

pytestmark = pytest.mark.bdd

scenarios("inbox/job_board_imports.feature")

OFFERS_URL = "/api/v1/offers"
JOB_BOARDS_URL = "/api/v1/job-boards"
FEED_HOSTS = {
    "remoteok.com": "remoteok",
    "remotive.com": "remotive",
    "himalayas.app": "himalayas",
    "jobicy.com": "jobicy",
}

# The RSS of each job board imported from one, by host; the RSS is read once per title.
RSS_HOSTS = {"www.evenbreak.com": "Evenbreak"}
RSS_QUERY = "keywords"

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
    # One page, the last one: `nextCursor` is the `cursor` that asks for the page after it.
    return {"jobs": jobs, "nextCursor": None, "hasMore": False}


def _rss(rows: list[Row]) -> str:
    """Evenbreak's RSS, as served on 2026-11-11: the company goes in the item title."""
    items = "".join(
        f"<item><title>{escape(r['title'])}</title>"
        f"<description>{escape(r['description'])}</description>"
        f'<link>{escape(r["link"])}</link><guid isPermaLink="true">{escape(r["link"])}</guid>'
        "</item>"
        for r in rows
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel>'
        f"<title>Job Search RSS</title>{items}</channel></rss>"
    )


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
    job_boards: dict[str, dict[str, str]] = field(default_factory=dict)
    published: dict[str, list[Row]] = field(default_factory=dict)
    # The feeds that publish in pages, each page asked for with the cursor the one before gave.
    pages: dict[str, list[list[Row]]] = field(default_factory=dict)
    unavailable: set[str] = field(default_factory=set)
    searched: dict[str, list[str]] = field(default_factory=dict)
    # RSS items by job board and title searched; `rss_any` answers every other title.
    rss: defaultdict[str, dict[str, list[Row]]] = field(default_factory=lambda: defaultdict(dict))
    rss_any: dict[str, list[Row]] = field(default_factory=dict)
    rss_invalid: set[str] = field(default_factory=set)
    rss_reads: dict[str, list[str]] = field(default_factory=dict)
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

    def answer_rss(request: httpx2.Request) -> httpx2.Response:
        job_board = RSS_HOSTS[request.url.host]
        state.rss_reads.setdefault(job_board, []).append(str(request.url))
        if job_board in state.unavailable:
            return httpx2.Response(503)
        if job_board in state.rss_invalid:
            return httpx2.Response(200, text="<html><body>Not found</body></html>")
        query = request.url.params[RSS_QUERY]
        rows = state.rss[job_board].get(query, state.rss_any.get(job_board, []))
        return httpx2.Response(200, text=_rss(rows))

    def answer(request: httpx2.Request) -> httpx2.Response:
        if request.url.host in RSS_HOSTS:
            return answer_rss(request)
        feed = FEED_HOSTS[request.url.host]
        if "q" in request.url.params:
            state.searched.setdefault(feed, []).append(request.url.params["q"])
        if feed in state.unavailable:
            return httpx2.Response(503)
        if feed in state.pages:
            return httpx2.Response(200, json=_page(state.pages[feed], request))
        return httpx2.Response(200, json=FEED_PAYLOADS[feed](state.published.get(feed, [])))

    async def fake_client() -> AsyncIterator[httpx2.AsyncClient]:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(answer)) as fake:
            yield fake

    overrides = cast(FastAPI, client.app).dependency_overrides
    overrides[get_feed_client] = fake_client
    yield
    overrides.pop(get_feed_client, None)


def _page(pages: list[list[Row]], request: httpx2.Request) -> object:
    """Jobicy's page for the cursor asked, as served on 2026-11-12; the first has no cursor."""
    index = int(request.url.params.get("cursor", "0"))
    more = index + 1 < len(pages)
    page = cast(dict[str, object], _jobicy(pages[index]))
    return page | {"nextCursor": str(index + 1) if more else None, "hasMore": more}


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


def _add_job_board(
    client: TestClient, state: ScenarioState, name: str, source: dict[str, str] | None = None
) -> None:
    body = {"name": name, "search_url_template": "https://jobs.example/?q={query}"}
    body |= {"syntax": "keywords"} | (source or {})
    response = client.post(JOB_BOARDS_URL, json=body)
    assert response.status_code == 201, response.text
    state.job_boards[name] = response.json()


def _import(client: TestClient, state: ScenarioState, job_board: str) -> httpx2.Response:
    return client.post(f"{JOB_BOARDS_URL}/{state.job_boards[job_board]['id']}/imports")


def _offer(client: TestClient, title: str) -> dict[str, Any]:
    response = client.get(OFFERS_URL)
    assert response.status_code == 200, response.text
    offers: list[dict[str, Any]] = response.json()["items"]
    return next(offer for offer in offers if offer["title"] == title)


def _add_offer(
    client: TestClient,
    state: ScenarioState,
    company: str,
    title: str,
    job_board: str | None = None,
) -> str:
    body = {"url": f"https://jobs.example/{next(state.urls)}", "company": company, "title": title}
    if job_board is not None:
        body["job_board_id"] = state.job_boards[job_board]["id"]
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


@given(parsers.parse('the feed "{feed}" publishes {pages:d} pages of {size:d} offers'))
def given_feed_publishes_pages(state: ScenarioState, feed: str, pages: int, size: int) -> None:
    numbers = count(1)
    state.pages[feed] = [
        [
            {
                "title": f"Role {number}",
                "company": f"Company {number}",
                "description": "Remote",
                "url": f"https://jobicy.com/jobs/{number}",
            }
            for number in (next(numbers) for _ in range(size))
        ]
        for _ in range(pages)
    ]


@given(parsers.parse('the feed "{feed}" is not available'))
def given_feed_down(state: ScenarioState, feed: str) -> None:
    state.unavailable.add(feed)


@given("the job boards imported from a feed:")
def given_imported_job_boards(
    client: TestClient, state: ScenarioState, datatable: list[list[str]]
) -> None:
    for row in _rows(datatable):
        _add_job_board(client, state, row["name"], {"import_method": "api", "feed": row["feed"]})


@given(parsers.re(r'a job board named "(?P<name>[^"]+)"$'))
def given_job_board(client: TestClient, state: ScenarioState, name: str) -> None:
    _add_job_board(client, state, name)


@given(parsers.parse('a job board named "{name}" imported from the RSS "{template}"'))
def given_rss_job_board(client: TestClient, state: ScenarioState, name: str, template: str) -> None:
    _add_job_board(client, state, name, {"import_method": "rss", "rss_url_template": template})


@given(parsers.parse('a job board named "{name}" imported from the email alert "{email_alert}"'))
def given_email_job_board(
    client: TestClient, state: ScenarioState, name: str, email_alert: str
) -> None:
    _add_job_board(client, state, name, {"import_method": "email", "email_alert": email_alert})


@given(parsers.parse('the RSS of "{job_board}" publishes for "{title}":'))
def given_rss_publishes(
    state: ScenarioState, job_board: str, title: str, datatable: list[list[str]]
) -> None:
    state.rss[job_board][title] = _rows(datatable)


@given(parsers.parse('the RSS of "{job_board}" publishes nothing'))
def given_rss_publishes_nothing(state: ScenarioState, job_board: str) -> None:
    state.rss[job_board].clear()
    state.rss_any[job_board] = []


@given(parsers.parse('the RSS of "{job_board}" is not available'))
def given_rss_down(state: ScenarioState, job_board: str) -> None:
    state.unavailable.add(job_board)


@given(parsers.parse('the RSS of "{job_board}" is not a valid RSS'))
def given_rss_invalid(state: ScenarioState, job_board: str) -> None:
    state.rss_invalid.add(job_board)


def _imported_at(client: TestClient, state: ScenarioState, job_board: str, moment: str) -> None:
    assert state.now is not None, "the scenario must set the time first"
    _set_time(client, _moment(moment))
    response = _import(client, state, job_board)
    assert response.status_code == 201, response.text
    _set_time(client, state.now)


@given(parsers.re(r'the job board "(?P<job_board>[^"]+)" was imported at (?P<moment>[0-9: -]+)$'))
def given_job_board_imported(
    client: TestClient, state: ScenarioState, job_board: str, moment: str
) -> None:
    _imported_at(client, state, job_board, moment)


@given(parsers.parse('the job board "{job_board}" was imported at {moment} with:'))
def given_job_board_imported_with(
    client: TestClient,
    state: ScenarioState,
    job_board: str,
    moment: str,
    datatable: list[list[str]],
) -> None:
    rows = _rows(datatable)
    feed = state.job_boards[job_board]["feed"]
    if feed is None:
        # An RSS: its items read "Company: Title" and come back for every title.
        state.rss_any[job_board] = [
            {
                "title": f"{r['company']}: {r['title']}",
                "description": r["description"],
                "link": r["url"],
            }
            for r in rows
        ]
    else:
        state.published[feed] = rows
    _imported_at(client, state, job_board, moment)


@given(parsers.parse('I promoted the offer "{title}"'))
def given_promoted(client: TestClient, title: str) -> None:
    offer_id = _offer(client, title)["id"]
    response = client.post(f"{OFFERS_URL}/{offer_id}/promotion", json={})
    assert response.status_code == 201, response.text


@given(parsers.re(r'an offer for "(?P<company>[^"]+)" as "(?P<title>[^"]+)"$'))
def given_offer(client: TestClient, state: ScenarioState, company: str, title: str) -> None:
    _add_offer(client, state, company, title)


@given(parsers.parse('an offer for "{company}" as "{title}" from "{job_board}"'))
def given_offer_from(
    client: TestClient, state: ScenarioState, company: str, title: str, job_board: str
) -> None:
    _add_offer(client, state, company, title, job_board)


@given(parsers.parse('an offer for "{company}" as "{title}" that was discarded'))
def given_discarded_offer(
    client: TestClient, state: ScenarioState, company: str, title: str
) -> None:
    offer_id = _add_offer(client, state, company, title)
    response = client.post(f"{OFFERS_URL}/{offer_id}/discard", json={})
    assert response.status_code == 201, response.text


# --- When ---


@when(parsers.parse('I import the job board "{job_board}"'))
def when_import(client: TestClient, state: ScenarioState, job_board: str) -> None:
    state.response = _import(client, state, job_board)


@when("I import a nonexistent job board")
def when_import_nonexistent(client: TestClient, state: ScenarioState) -> None:
    state.response = client.post(f"{JOB_BOARDS_URL}/{uuid7()}/imports")


@when("I list the job boards")
def when_list_job_boards(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(JOB_BOARDS_URL)


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


@then(parsers.parse('the RSS of "{job_board}" was read at:'))
def then_rss_read_at(state: ScenarioState, job_board: str, datatable: list[list[str]]) -> None:
    assert state.rss_reads.get(job_board, []) == [url for (url,) in datatable]


@then(parsers.parse('the RSS of "{job_board}" was not read'))
def then_rss_not_read(state: ScenarioState, job_board: str) -> None:
    assert job_board not in state.rss_reads


@then("the pending offers are, with their company:")
def then_pending_offers_with_company(client: TestClient, datatable: list[list[str]]) -> None:
    response = client.get(OFFERS_URL, params={"status": "pending"})
    assert response.status_code == 200, response.text
    offers = [
        {"company": item["company"], "title": item["title"]} for item in response.json()["items"]
    ]
    assert offers == _rows(datatable)


@then(parsers.parse("the pending offers are: {titles}"))
def then_pending_offers(client: TestClient, titles: str) -> None:
    response = client.get(OFFERS_URL, params={"status": "pending"})
    assert response.status_code == 200, response.text
    expected = re.findall(r'"([^"]*)"', titles)
    assert [item["title"] for item in response.json()["items"]] == expected


@then(
    parsers.parse('the offer "{title}" links to "{url}" and comes from the job board "{job_board}"')
)
def then_offer_source(client: TestClient, title: str, url: str, job_board: str) -> None:
    offer = _offer(client, title)
    assert (offer["url"], offer["job_board_name"]) == (url, job_board)


@then(parsers.parse('the offer "{title}" is for the company "{company}"'))
def then_offer_company(client: TestClient, title: str, company: str) -> None:
    assert _offer(client, title)["company"] == company


@then(parsers.re(r'the offer "(?P<title>[^"]+)" is "(?P<status>[^"]+)"$'))
def then_offer_status(client: TestClient, title: str, status: str) -> None:
    assert _offer(client, title)["status"] == status


@then(parsers.parse('the offer "{title}" is "{status}" with reason "{reason}"'))
def then_offer_status_reason(client: TestClient, title: str, status: str, reason: str) -> None:
    offer = _offer(client, title)
    assert (offer["status"], offer["discard_reason"]) == (status, reason)


@then(
    parsers.parse("it is rejected because the job board was imported too recently, until {moment}")
)
def then_cooldown(state: ScenarioState, moment: str) -> None:
    assert state.now is not None
    _assert_problem(state, 429, "feed-cooldown")
    wait = (_moment(moment) - state.now).total_seconds()
    assert int(state.last_response.headers["Retry-After"]) == int(wait)


REJECTIONS = {
    "the feed is not available": (502, "feed-unavailable"),
    "the job board is not imported": (409, "job-board-not-imported"),
    "the job board is imported from its email alerts": (409, "job-board-imported-by-email"),
    "the job board does not exist": (404, "not-found"),
}


@then(parsers.re(f"it is rejected because (?P<reason>{'|'.join(REJECTIONS)})$"))
def then_rejected(state: ScenarioState, reason: str) -> None:
    _assert_problem(state, *REJECTIONS[reason])


@then(parsers.parse('the job board "{job_board}" has never been imported'))
def then_never_imported(client: TestClient, state: ScenarioState, job_board: str) -> None:
    response = client.get(f"{JOB_BOARDS_URL}/{state.job_boards[job_board]['id']}")
    assert response.status_code == 200, response.text
    assert response.json()["last_imported_at"] is None


@then("the job boards are:")
def then_job_boards_are(state: ScenarioState, datatable: list[list[str]]) -> None:
    response = state.last_response
    assert response.status_code == 200, response.text
    actual = [
        {
            "name": item["name"],
            "import_method": item["import_method"],
            "last_imported_at": _local(item["last_imported_at"]),
            "next_import_at": _local(item["next_import_at"]),
        }
        for item in response.json()["items"]
    ]
    assert actual == _rows(datatable)
