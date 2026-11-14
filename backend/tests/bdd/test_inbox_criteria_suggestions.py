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

scenarios("inbox/criteria_suggestions.feature")

OFFERS_URL = "/api/v1/offers"
PROFILES_URL = "/api/v1/search-profiles"
SUGGESTIONS_URL = "/api/v1/criteria-suggestions"
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
    def suggestions(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = _ok(self.last_response, 200)["items"]
        return items


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


def _quoted(text: str) -> list[str]:
    return re.findall(r'"([^"]*)"', text)


def _profile_id(client: TestClient, name: str) -> str:
    items = _ok(client.get(PROFILES_URL), 200)["items"]
    profile_id: str = next(p["id"] for p in items if p["name"] == name)
    return profile_id


def _offer_ids(client: TestClient) -> dict[str, str]:
    items = _ok(client.get(OFFERS_URL, params={"limit": "100"}), 200)["items"]
    return {item["company"]: item["id"] for item in items}


def _dismiss(client: TestClient, profile_id: str, word: str) -> httpx2.Response:
    body = {"search_profile_id": profile_id, "word": word}
    return client.post(f"{SUGGESTIONS_URL}/dismissals", json=body)


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


@given(parsers.re(r"I discarded the offers of (?P<companies>.+)"))
def given_discarded(client: TestClient, companies: str) -> None:
    ids = _offer_ids(client)
    for company in _quoted(companies):
        _ok(client.post(f"{OFFERS_URL}/{ids[company]}/discard", json={}))


@given(parsers.parse('I promoted the offer of "{company}"'))
def given_promoted(client: TestClient, company: str) -> None:
    _ok(client.post(f"{OFFERS_URL}/{_offer_ids(client)[company]}/promotion", json={}))


@given(parsers.parse('the profile "{name}" excludes "{word}"'))
def given_excludes(client: TestClient, name: str, word: str) -> None:
    url = f"{PROFILES_URL}/{_profile_id(client, name)}"
    _ok(client.patch(url, json={"excluded_keywords": [word]}), 200)


@given(parsers.parse('I said "Not now" to excluding "{word}" from "{name}"'))
def given_dismissed(client: TestClient, word: str, name: str) -> None:
    _ok(_dismiss(client, _profile_id(client, name), word))


# --- When ---


@when("I list the suggestions")
def when_list(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(SUGGESTIONS_URL)


@when(parsers.re(r'I say "Not now" to excluding "(?P<word>[^"]+)" from "(?P<name>[^"]+)"$'))
def when_dismiss(client: TestClient, state: ScenarioState, word: str, name: str) -> None:
    state.response = _dismiss(client, _profile_id(client, name), word)


@when(parsers.parse('I say "Not now" to excluding "{word}" from a nonexistent profile'))
def when_dismiss_nonexistent(client: TestClient, state: ScenarioState, word: str) -> None:
    state.response = _dismiss(client, str(uuid7()), word)


# --- Then ---


@then(
    parsers.parse(
        'the only suggestion is to exclude "{word}" from "{name}", '
        "in {offers:d} of the {discarded:d} discarded"
    )
)
def then_only(state: ScenarioState, word: str, name: str, offers: int, discarded: int) -> None:
    [suggestion] = state.suggestions
    found = (
        suggestion["word"],
        suggestion["search_profile_name"],
        len(suggestion["offer_ids"]),
        suggestion["discarded"],
    )
    assert found == (word, name, offers, discarded)


@then(parsers.re(r"it takes (?P<leaving>\d+) offers? out of Pending and loses none I promoted"))
def then_preview(state: ScenarioState, leaving: str) -> None:
    preview = state.suggestions[0]["preview"]
    assert (preview["leaving_pending"], preview["promoted_filtered"]) == (int(leaving), 0)


@then(parsers.re(r"it is backed by the offers of (?P<companies>.+)"))
def then_backed(client: TestClient, state: ScenarioState, companies: str) -> None:
    ids = _offer_ids(client)
    expected = {ids[company] for company in _quoted(companies)}
    assert set(state.suggestions[0]["offer_ids"]) == expected


@then("there are no suggestions")
def then_none(state: ScenarioState) -> None:
    assert state.suggestions == []


@then("it is accepted")
def then_accepted(state: ScenarioState) -> None:
    assert state.last_response.status_code == 201, state.last_response.text


@then("it is rejected because it does not exist")
def then_not_found(state: ScenarioState) -> None:
    response = state.last_response
    assert (response.status_code, response.json()["type"]) == (404, "/problems/not-found")
