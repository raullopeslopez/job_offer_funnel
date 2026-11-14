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

scenarios("inbox/frequent_titles.feature")

OFFERS_URL = "/api/v1/offers"
PROFILES_URL = "/api/v1/search-profiles"
TITLES_URL = f"{OFFERS_URL}/frequent-titles"
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

    @property
    def found(self) -> dict[str, Any]:
        found: dict[str, Any] = _ok(self.last_response, 200)
        return found


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


def _ok(response: httpx2.Response, status: int = 201) -> Any:
    assert response.status_code == status, response.text
    return response.json() if response.content else {}


def _key(title: str) -> str:
    return " ".join(title.split()).casefold()


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
    _ok(client.post(PROFILES_URL, json=body))


@given(parsers.parse('the job board "Remote OK" was imported with:'))
def given_imported(client: TestClient, state: ScenarioState, datatable: list[list[str]]) -> None:
    header, *rows = datatable
    state.remoteok = [dict(zip(header, values, strict=True)) for values in rows]
    _ok(client.post(f"/api/v1/job-boards/{state.remoteok_id}/imports"))


@given(parsers.parse('I discarded the offer of "{company}"'))
def given_discarded(client: TestClient, company: str) -> None:
    items = _ok(client.get(OFFERS_URL, params={"limit": "100"}), 200)["items"]
    offer_id = next(o["id"] for o in items if o["company"] == company)
    _ok(client.post(f"{OFFERS_URL}/{offer_id}/discard", json={}))


# --- When ---


@when(parsers.parse('I list the frequent titles for the profile "{name}"'))
def when_list(client: TestClient, state: ScenarioState, name: str) -> None:
    items = _ok(client.get(PROFILES_URL), 200)["items"]
    profile_id = next(p["id"] for p in items if p["name"] == name)
    state.response = client.get(TITLES_URL, params={"search_profile_id": profile_id})


@when("I list the frequent titles for a nonexistent profile")
def when_list_nonexistent(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(TITLES_URL, params={"search_profile_id": str(uuid7())})


# --- Then ---


@then(parsers.parse("{offers:d} offers have no title of the profile"))
def then_offers(state: ScenarioState, offers: int) -> None:
    assert state.found["offers"] == offers


@then("the frequent titles are:")
def then_titles(state: ScenarioState, datatable: list[list[str]]) -> None:
    _, *rows = datatable
    expected = [
        (title, int(offers), int(keywords), int(reading), int(entering))
        for title, offers, keywords, reading, entering in rows
    ]
    found = [
        (
            t["title"],
            t["offers"],
            t["with_keywords"],
            t["reading_passes"],
            t["preview"]["entering_pending"],
        )
        for t in state.found["titles"]
    ]
    assert found == expected


@then(parsers.parse('the frequent title "{title}" has {offers:d} offers'))
def then_title_offers(state: ScenarioState, title: str, offers: int) -> None:
    found = {_key(t["title"]): t["offers"] for t in state.found["titles"]}
    assert found[_key(title)] == offers


@then("it is rejected because it does not exist")
def then_not_found(state: ScenarioState) -> None:
    response = state.last_response
    assert (response.status_code, response.json()["type"]) == (404, "/problems/not-found")
