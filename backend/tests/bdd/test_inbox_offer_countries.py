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

scenarios("inbox/offer_countries.feature")

OFFERS_URL = "/api/v1/offers"
JOB_BOARDS_URL = "/api/v1/job-boards"
WATCHED_URL = "/api/v1/watched-companies"
ALERTS_URL = "/api/v1/email-alerts/imports"
LINKEDIN_SENDER = "jobalerts-noreply@linkedin.com"
HOSTS = {
    "remoteok.com": "remoteok",
    "remotive.com": "remotive",
    "himalayas.app": "himalayas",
    "jobicy.com": "jobicy",
    "boards-api.greenhouse.io": "greenhouse",
    "api.lever.co": "lever",
    "api.ashbyhq.com": "ashby",
}


@dataclass(frozen=True)
class Job:
    title: str
    company: str
    url: str
    # As the source publishes it: a text, a list (Himalayas) or nothing.
    location: str | list[str] | None


def _remoteok(jobs: list[Job]) -> object:
    items: list[dict[str, object]] = [
        {"position": j.title, "company": j.company, "description": "", "url": j.url}
        | ({} if j.location is None else {"location": j.location})
        for j in jobs
    ]
    return [{"legal": "Link back to Remote OK and mention it as the source."}, *items]


def _remotive(jobs: list[Job]) -> object:
    items = [
        {
            "title": j.title,
            "company_name": j.company,
            "description": "",
            "url": j.url,
            "candidate_required_location": j.location,
        }
        for j in jobs
    ]
    return {"jobs": items}


def _himalayas(jobs: list[Job]) -> object:
    items = [
        {
            "title": j.title,
            "companyName": j.company,
            "description": "",
            "applicationLink": j.url,
            "locationRestrictions": j.location,
        }
        for j in jobs
    ]
    return {"jobs": items}


def _jobicy(jobs: list[Job]) -> object:
    items = [
        {
            "jobTitle": j.title,
            "companyName": j.company,
            "jobDescription": "",
            "url": j.url,
            "jobGeo": j.location,
        }
        for j in jobs
    ]
    return {"jobs": items, "nextCursor": None, "hasMore": False}


def _greenhouse(jobs: list[Job]) -> object:
    items = [
        {
            "id": index,
            "title": j.title,
            "content": "",
            "absolute_url": j.url,
            "location": {"name": j.location},
        }
        for index, j in enumerate(jobs)
    ]
    return {"jobs": items, "meta": {"total": len(items)}}


def _lever(jobs: list[Job]) -> object:
    return [
        {
            "id": str(index),
            "text": j.title,
            "descriptionPlain": "",
            "hostedUrl": j.url,
            "categories": {"commitment": "Full-time", "location": j.location},
        }
        for index, j in enumerate(jobs)
    ]


def _ashby(jobs: list[Job]) -> object:
    items = [
        {
            "id": str(index),
            "title": j.title,
            "descriptionPlain": "",
            "jobUrl": j.url,
            "isListed": True,
            "location": j.location,
        }
        for index, j in enumerate(jobs)
    ]
    return {"apiVersion": "1", "jobs": items}


# Where each source puts the location, checked against the live APIs on 2026-11-14.
PAYLOADS = {
    "remoteok": _remoteok,
    "remotive": _remotive,
    "himalayas": _himalayas,
    "jobicy": _jobicy,
    "greenhouse": _greenhouse,
    "lever": _lever,
    "ashby": _ashby,
}


def _linkedin_alert(rows: list[dict[str, str]]) -> str:
    """A LinkedIn job alert's plain-text body, shaped like the real ones (2026-11-11)."""
    separator = "\n\n---------------------------------------------------------\n\n"
    jobs = [
        f"{r['title']}\n{r['company']}\n{r['location']}\nCrecimiento rápido\n\n1 contacto\n"
        f"Ver anuncio de empleo: https://www.linkedin.com/comm/jobs/view/{r['job']}/?trk=eml"
        for r in rows
    ]
    footer = "Gestionar tus alertas de empleo: https://www.linkedin.com/comm/jobs/alerts"
    return "Tu alerta de empleo para Backend Engineer\n" + separator.join([*jobs, footer])


@dataclass
class ScenarioState:
    job_boards: dict[str, str] = field(default_factory=dict)
    watched: dict[str, str] = field(default_factory=dict)
    # By source: the feed, or the ATS of a watched company.
    published: dict[str, list[Job]] = field(default_factory=dict)
    urls: count[int] = field(default_factory=count)

    def publish(self, source: str, title: str, location: str | list[str] | None) -> None:
        url = f"https://{source}.example/jobs/{next(self.urls)}"
        self.published.setdefault(source, []).append(Job(title, "Acme", url, location))


@pytest.fixture
def state() -> ScenarioState:
    return ScenarioState()


@pytest.fixture(autouse=True)
def fake_sources(client: TestClient, state: ScenarioState) -> Iterator[None]:
    """Every feed and ATS request is answered from the scenario: no internet."""

    def answer(request: httpx2.Request) -> httpx2.Response:
        source = HOSTS[request.url.host]
        return httpx2.Response(200, json=PAYLOADS[source](state.published.get(source, [])))

    async def fake_client() -> AsyncIterator[httpx2.AsyncClient]:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(answer)) as fake:
            yield fake

    overrides = cast(FastAPI, client.app).dependency_overrides
    overrides[get_feed_client] = fake_client
    yield
    overrides.pop(get_feed_client, None)


def _add_job_board(client: TestClient, state: ScenarioState, body: dict[str, str]) -> None:
    body = {"search_url_template": "https://jobs.example/?q={query}", "syntax": "keywords"} | body
    response = client.post(JOB_BOARDS_URL, json=body)
    assert response.status_code == 201, response.text
    state.job_boards[body["name"]] = response.json()["id"]


def _offer(client: TestClient, title: str) -> dict[str, Any]:
    response = client.get(OFFERS_URL)
    assert response.status_code == 200, response.text
    offers: list[dict[str, Any]] = response.json()["items"]
    return next(offer for offer in offers if offer["title"] == title)


# --- Given ---


@given(parsers.parse("the time is {moment}"))
def given_time(client: TestClient, moment: str) -> None:
    clock = FixedClock(datetime.fromisoformat(moment).replace(tzinfo=ZONE))
    cast(FastAPI, client.app).dependency_overrides[get_clock] = lambda: clock


@given(parsers.parse('a search profile named "{name}" with:'))
def given_profile(client: TestClient, name: str, datatable: list[list[str]]) -> None:
    body: dict[str, Any] = {"name": name}
    for key, value in datatable:
        body[key] = re.split(r"\s*,\s*", value)
    response = client.post("/api/v1/search-profiles", json=body)
    assert response.status_code == 201, response.text


@given("the job boards imported from a feed:")
def given_feed_job_boards(
    client: TestClient, state: ScenarioState, datatable: list[list[str]]
) -> None:
    _header, *rows = datatable
    for name, feed in rows:
        _add_job_board(client, state, {"name": name, "import_method": "api", "feed": feed})


@given(parsers.parse('a job board named "{name}" imported from the email alert "{email_alert}"'))
def given_email_job_board(
    client: TestClient, state: ScenarioState, name: str, email_alert: str
) -> None:
    body = {"name": name, "import_method": "email", "email_alert": email_alert}
    _add_job_board(client, state, body)


@given(
    parsers.re(
        r'the feed "(?P<feed>[^"]+)" publishes an offer for "Acme" as "(?P<title>[^"]+)" '
        r'located in "(?P<location>[^"]*)"$'
    )
)
def given_feed_offer(state: ScenarioState, feed: str, title: str, location: str) -> None:
    # Himalayas publishes a list of locations.
    state.publish(feed, title, [location] if feed == "himalayas" else location)


@given(
    parsers.parse(
        'the feed "{feed}" publishes an offer for "Acme" as "{title}" located in '
        '"{first}" and "{second}"'
    )
)
def given_feed_offer_in_two(
    state: ScenarioState, feed: str, title: str, first: str, second: str
) -> None:
    state.publish(feed, title, [first, second])


@given(
    parsers.parse('the feed "{feed}" publishes an offer for "Acme" as "{title}" with no location')
)
def given_feed_offer_nowhere(state: ScenarioState, feed: str, title: str) -> None:
    state.publish(feed, title, None)


@given(parsers.parse('the company "{name}" is watched on "{ats}" with board "{board}"'))
def given_watched(
    client: TestClient, state: ScenarioState, name: str, ats: str, board: str
) -> None:
    response = client.post(WATCHED_URL, json={"name": name, "ats": ats, "board": board})
    assert response.status_code == 201, response.text
    state.watched[name] = response.json()["id"]
    state.published.setdefault(ats, [])


@given(parsers.parse('the board of "{company}" publishes "{title}" located in "{location}"'))
def given_board_offer(
    client: TestClient, state: ScenarioState, company: str, title: str, location: str
) -> None:
    response = client.get(WATCHED_URL)
    assert response.status_code == 200, response.text
    ats = next(w["ats"] for w in response.json() if w["name"] == company)
    state.publish(ats, title, location)


@given("a LinkedIn job alert with:", target_fixture="alert")
def given_alert(datatable: list[list[str]]) -> str:
    header, *rows = datatable
    return _linkedin_alert([dict(zip(header, values, strict=True)) for values in rows])


# --- When ---


@when(parsers.parse('I import the job board "{job_board}"'))
def when_import_job_board(client: TestClient, state: ScenarioState, job_board: str) -> None:
    response = client.post(f"{JOB_BOARDS_URL}/{state.job_boards[job_board]}/imports")
    assert response.status_code == 201, response.text


@when(parsers.parse('I import the watched company "{company}"'))
def when_import_watched(client: TestClient, state: ScenarioState, company: str) -> None:
    response = client.post(f"{WATCHED_URL}/{state.watched[company]}/imports")
    assert response.status_code == 201, response.text


@when("I import the alert")
def when_import_alert(client: TestClient, alert: str) -> None:
    response = client.post(ALERTS_URL, json={"sender": LINKEDIN_SENDER, "text": alert})
    assert response.status_code == 201, response.text


@when(parsers.parse('I add an offer for "{company}" as "{title}"'))
def when_add_offer(client: TestClient, company: str, title: str) -> None:
    body = {"url": "https://jobs.example/1", "company": company, "title": title}
    response = client.post(OFFERS_URL, json=body)
    assert response.status_code == 201, response.text


# --- Then ---


@then(parsers.parse('the offer "{title}" is located in "{location}"'))
def then_located_in(client: TestClient, title: str, location: str) -> None:
    assert _offer(client, title)["location"] == location


@then(parsers.parse('the offer "{title}" has no location'))
def then_no_location(client: TestClient, title: str) -> None:
    offer = _offer(client, title)
    assert (offer["location"], offer["countries"]) == (None, [])


@then(parsers.re(r'the offer "(?P<title>[^"]+)" is from "(?P<countries>[^"]+)"$'))
def then_from(client: TestClient, title: str, countries: str) -> None:
    assert _offer(client, title)["countries"] == countries.split(", ")


@then(parsers.parse('the offer "{title}" is from no known country'))
def then_from_nowhere(client: TestClient, title: str) -> None:
    assert _offer(client, title)["countries"] == []
