import asyncio
import re
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from itertools import count
from typing import Any, cast

import asyncpg
import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when
from support.postgres import asyncpg_dsn

from funnel.core.config import Settings
from funnel.modules.inbox.router import get_feed_client

pytestmark = pytest.mark.bdd

scenarios("inbox/offer_variants.feature")

URL = "/api/v1/offers"
_OFFER = r'an offer for "(?P<company>[^"]*)" as "(?P<title>[^"]*)"'


@dataclass
class ScenarioState:
    remoteok: list[dict[str, str]] = field(default_factory=list)
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
def fake_feed(client: TestClient, state: ScenarioState) -> Iterator[None]:
    """Remote OK answers from the scenario: tests never reach the internet."""

    def answer(_request: httpx2.Request) -> httpx2.Response:
        jobs = [{"position": job["title"], **job} for job in state.remoteok]
        return httpx2.Response(200, json=[{"legal": "Link back to Remote OK."}, *jobs])

    async def fake_client() -> AsyncIterator[httpx2.AsyncClient]:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(answer)) as fake:
            yield fake

    overrides = cast(FastAPI, client.app).dependency_overrides
    overrides[get_feed_client] = fake_client
    yield
    overrides.pop(get_feed_client, None)


def _rows(datatable: list[list[str]]) -> list[dict[str, str]]:
    header, *rows = datatable
    return [dict(zip(header, row, strict=True)) for row in rows]


def _add_offer(client: TestClient, state: ScenarioState, company: str, title: str) -> str:
    body = {"url": f"https://jobs.example/{next(state.urls)}", "company": company, "title": title}
    response = client.post(URL, json=body)
    assert response.status_code == 201, response.text
    offer_id: str = response.json()["id"]
    return offer_id


async def _execute(database_url: str, statement: str, *arguments: str) -> None:
    connection = await asyncpg.connect(asyncpg_dsn(database_url))
    try:
        await connection.execute(statement, *arguments)
    finally:
        await connection.close()


def _offer(client: TestClient, title: str) -> dict[str, Any]:
    response = client.get(URL, params={"limit": 100})
    assert response.status_code == 200, response.text
    (offer,) = [item for item in response.json()["items"] if item["title"] == title]
    return cast(dict[str, Any], offer)


# --- Given ---


@given(parsers.re(f"{_OFFER}$"))
def given_offer(client: TestClient, state: ScenarioState, company: str, title: str) -> None:
    _add_offer(client, state, company, title)


@given(parsers.re(f"{_OFFER} that was (?P<decided>discarded|promoted)$"))
def given_decided_offer(
    client: TestClient, state: ScenarioState, company: str, title: str, decided: str
) -> None:
    offer_id = _add_offer(client, state, company, title)
    action = {"discarded": "discard", "promoted": "promotion"}[decided]
    response = client.post(f"{URL}/{offer_id}/{action}", json={})
    assert response.status_code == 201, response.text


@given(parsers.parse('a search profile named "{name}" with:'))
def given_profile(client: TestClient, name: str, datatable: list[list[str]]) -> None:
    body: dict[str, Any] = {"name": name}
    for key, value in datatable:
        body[key] = re.split(r"\s*,\s*", value)
    response = client.post("/api/v1/search-profiles", json=body)
    assert response.status_code == 201, response.text


@given(parsers.parse('a job board named "Remote OK" imported from the feed "remoteok"'))
def given_remoteok_job_board(client: TestClient) -> None:
    body = {
        "name": "Remote OK",
        "search_url_template": "https://remoteok.com/?q={query}",
        "syntax": "keywords",
        "import_method": "api",
        "feed": "remoteok",
    }
    response = client.post("/api/v1/job-boards", json=body)
    assert response.status_code == 201, response.text


@given(parsers.parse('the job board "Remote OK" was imported with:'))
def given_imported(client: TestClient, state: ScenarioState, datatable: list[list[str]]) -> None:
    state.remoteok = _rows(datatable)
    (job_board,) = client.get("/api/v1/job-boards").json()["items"]
    response = client.post(f"/api/v1/job-boards/{job_board['id']}/imports")
    assert response.status_code == 201, response.text


@given("these offers, added in this order:")
def given_offers_in_order(
    client: TestClient, state: ScenarioState, settings: Settings, datatable: list[list[str]]
) -> None:
    for row in _rows(datatable):
        offer_id = _add_offer(client, state, row["company"], row["title"])
        if verdict := row.get("verdict"):
            # No endpoint sets a verdict without a triager: it is written as the triage would.
            asyncio.run(
                _execute(
                    settings.database_url,
                    "UPDATE offers SET verdict = $1, triaged_at = now() WHERE id = $2::uuid",
                    verdict.lower(),
                    offer_id,
                )
            )


# --- When ---


@when("I look at the offer")
def when_look_at_the_offer(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(URL)


@when(parsers.parse('I look at the offer "{title}"'))
def when_look_at_offer(client: TestClient, state: ScenarioState, title: str) -> None:
    state.response = client.get(f"{URL}/{_offer(client, title)['id']}")


@when("I list the pending offers with their variants together")
def when_list_together(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(URL, params={"status": "pending", "variants_together": "true"})


@when("I list the pending offers by verdict with their variants together")
def when_list_by_verdict_together(client: TestClient, state: ScenarioState) -> None:
    params = {"status": "pending", "by_verdict": "true", "variants_together": "true"}
    state.response = client.get(URL, params=params)


# --- Then ---


@then(parsers.parse('its base title is "{base_title}"'))
def then_base_title(state: ScenarioState, base_title: str) -> None:
    (offer,) = state.last_response.json()["items"]
    assert offer["base_title"] == base_title


@then(parsers.re(r"it has (?P<number>\d+) variants?$"))
def then_variants(state: ScenarioState, number: str) -> None:
    assert state.last_response.json()["variants"] == int(number)


@then(parsers.parse('the offers are, in order: "{titles}"'))
def then_offers_in_order(state: ScenarioState, titles: str) -> None:
    listed = [item["title"] for item in state.last_response.json()["items"]]
    assert listed == titles.split(", ")


@then(parsers.re(r'the offer "(?P<title>[^"]+)" has (?P<number>\d+) variants$'))
def then_offer_variants(client: TestClient, title: str, number: str) -> None:
    assert _offer(client, title)["variants"] == int(number)
