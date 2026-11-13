import re
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from typing import Any, cast
from uuid import uuid7

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from funnel.modules.inbox.router import get_feed_client

pytestmark = pytest.mark.bdd

scenarios("inbox/rescues.feature")

OFFERS_URL = "/api/v1/offers"
LIST_FIELDS = frozenset({"titles", "keywords", "excluded_keywords"})

Row = dict[str, str]


@dataclass
class ScenarioState:
    remoteok: list[Row] = field(default_factory=list)
    remoteok_id: str | None = None
    response: httpx2.Response | None = None

    @property
    def last_response(self) -> httpx2.Response:
        assert self.response is not None, "no request was made in this scenario"
        return self.response


@pytest.fixture
def state() -> ScenarioState:
    return ScenarioState()


@pytest.fixture(autouse=True)
def fake_remoteok(client: TestClient, state: ScenarioState) -> Iterator[None]:
    """Remote OK answers from the scenario: tests never reach the internet."""

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
    yield
    overrides.pop(get_feed_client, None)


def _ok(response: httpx2.Response, status: int = 201) -> dict[str, Any]:
    assert response.status_code == status, response.text
    body: dict[str, Any] = response.json() if response.content else {}
    return body


def _quoted(text: str) -> list[str]:
    return re.findall(r'"([^"]*)"', text)


def _offer_id(client: TestClient, company: str) -> str:
    items = _ok(client.get(OFFERS_URL, params={"limit": "100"}), 200)["items"]
    offer_id: str = next(o["id"] for o in items if o["company"] == company)
    return offer_id


def _offer(client: TestClient, company: str) -> dict[str, Any]:
    return _ok(client.get(f"{OFFERS_URL}/{_offer_id(client, company)}"), 200)


def _mark_url(client: TestClient, company: str) -> str:
    return f"{OFFERS_URL}/{_offer_id(client, company)}/rightly-filtered"


def _promote(client: TestClient, company: str) -> httpx2.Response:
    return client.post(f"{OFFERS_URL}/{_offer_id(client, company)}/promotion", json={})


# --- Given ---


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


@given(parsers.parse('a search profile named "{name}" with:'))
def given_profile(client: TestClient, name: str, datatable: list[list[str]]) -> None:
    body: dict[str, Any] = {"name": name}
    for key, value in datatable:
        body[key] = re.split(r"\s*,\s*", value) if key in LIST_FIELDS else value
    _ok(client.post("/api/v1/search-profiles", json=body))


@given(parsers.parse('the job board "Remote OK" was imported with:'))
def given_imported(client: TestClient, state: ScenarioState, datatable: list[list[str]]) -> None:
    header, *rows = datatable
    state.remoteok = [dict(zip(header, values, strict=True)) for values in rows]
    _ok(client.post(f"/api/v1/job-boards/{state.remoteok_id}/imports"))


@given(parsers.parse('an offer for "{company}" as "{title}"'))
def given_offer(client: TestClient, company: str, title: str) -> None:
    body = {"url": "https://jobs.example/hand", "company": company, "title": title}
    _ok(client.post(OFFERS_URL, json=body))


@given(parsers.parse('I discarded the offer of "{company}"'))
def given_discarded(client: TestClient, company: str) -> None:
    _ok(client.post(f"{OFFERS_URL}/{_offer_id(client, company)}/discard", json={}))


@given(parsers.parse('I marked the offer of "{company}" as rightly filtered'))
def given_marked(client: TestClient, company: str) -> None:
    _ok(client.post(_mark_url(client, company)))


@given(parsers.parse('I promoted the offer of "{company}"'))
def given_promoted(client: TestClient, company: str) -> None:
    _ok(_promote(client, company))


# --- When ---


@when(parsers.parse('I promote the offer of "{company}"'))
def when_promote(client: TestClient, state: ScenarioState, company: str) -> None:
    state.response = _promote(client, company)


@when(parsers.parse('I mark the offer of "{company}" as rightly filtered'))
def when_mark(client: TestClient, state: ScenarioState, company: str) -> None:
    state.response = client.post(_mark_url(client, company))


@when("I mark a nonexistent offer as rightly filtered")
def when_mark_nonexistent(client: TestClient, state: ScenarioState) -> None:
    state.response = client.post(f"{OFFERS_URL}/{uuid7()}/rightly-filtered")


@when(parsers.parse('I undo the mark of the offer of "{company}"'))
def when_unmark(client: TestClient, state: ScenarioState, company: str) -> None:
    state.response = client.delete(_mark_url(client, company))


@when("I count the filtered offers")
def when_count(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(f"{OFFERS_URL}/filtered-counts")


# --- Then ---


@then(parsers.parse('the offer of "{company}" is "{review}" with the rules {rules}'))
def then_reviewed(client: TestClient, company: str, review: str, rules: str) -> None:
    offer = _offer(client, company)
    assert (offer["review"], offer["review_rules"]) == (review, _quoted(rules))


@then(parsers.parse('the offer of "{company}" has no review'))
def then_no_review(client: TestClient, company: str) -> None:
    offer = _offer(client, company)
    assert (offer["review"], offer["review_rules"]) == (None, [])


@then(parsers.parse('the offer of "{company}" is "{status}" and filtered'))
def then_filtered(client: TestClient, company: str, status: str) -> None:
    offer = _offer(client, company)
    assert (offer["status"], offer["filtered"]) == (status, True)


@then(parsers.parse("the near misses are the offers of: {companies}"))
def then_near_misses(client: TestClient, companies: str) -> None:
    params = {"status": "pending", "near_miss": "true"}
    items = _ok(client.get(OFFERS_URL, params=params), 200)["items"]
    assert [item["company"] for item in items] == _quoted(companies)


@then("it is rejected because the offer is not filtered")
def then_not_filtered(state: ScenarioState) -> None:
    response = state.last_response
    assert (response.status_code, response.json()["type"]) == (409, "/problems/offer-not-filtered")


@then("it is rejected because the offer does not exist")
def then_not_found(state: ScenarioState) -> None:
    response = state.last_response
    assert (response.status_code, response.json()["type"]) == (404, "/problems/not-found")


@then(parsers.parse("{reviewed:d} near misses were reviewed and {rescued:d} was rescued"))
def then_review_counts(state: ScenarioState, reviewed: int, rescued: int) -> None:
    counts = _ok(state.last_response, 200)
    assert (counts["reviewed_near_misses"], counts["rescued_near_misses"]) == (reviewed, rescued)
