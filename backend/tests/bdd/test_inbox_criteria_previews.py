import re
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import uuid7

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when
from support.clock import FixedClock

from funnel.core.clock import get_clock
from funnel.modules.inbox.router import get_feed_client

pytestmark = pytest.mark.bdd

scenarios("inbox/criteria_previews.feature")

OFFERS_URL = "/api/v1/offers"
PROFILES_URL = "/api/v1/search-profiles"
PREVIEWS_URL = f"{OFFERS_URL}/criteria-previews"
LIST_FIELDS = frozenset({"titles", "keywords", "excluded_keywords", "work_modes"})
# Past the 6 hours a job board waits between imports.
LATER = timedelta(hours=7)
# Words may be empty: "" clears a list.
PREVIEW = r'the profile "(?P<name>[^"]+)" with the (?P<field_name>\w+) "(?P<words>[^"]*)"'

Row = dict[str, str]


@dataclass
class ScenarioState:
    remoteok: list[Row] = field(default_factory=list)
    remoteok_id: str | None = None
    preview: dict[str, Any] | None = None
    filtered_before: set[str] = field(default_factory=set)
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
    overrides.pop(get_clock, None)


def _ok(response: httpx2.Response, status: int = 201) -> dict[str, Any]:
    assert response.status_code == status, response.text
    body: dict[str, Any] = response.json() if response.content else {}
    return body


def _words(field_name: str, words: str) -> list[str] | str:
    if field_name not in LIST_FIELDS:
        return words
    return re.split(r"\s*,\s*", words) if words else []


def _offers(client: TestClient) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = _ok(client.get(OFFERS_URL, params={"limit": "100"}), 200)["items"]
    return items


def _offer_id(client: TestClient, company: str) -> str:
    offer_id: str = next(o["id"] for o in _offers(client) if o["company"] == company)
    return offer_id


def _filtered(client: TestClient) -> set[str]:
    return {offer["company"] for offer in _offers(client) if offer["filtered"]}


def _profile_id(client: TestClient, name: str) -> str:
    items = _ok(client.get(PROFILES_URL), 200)["items"]
    profile_id: str = next(p["id"] for p in items if p["name"] == name)
    return profile_id


def _preview(client: TestClient, profile_id: str, field_name: str, words: str) -> httpx2.Response:
    body = {"search_profile_id": profile_id, field_name: _words(field_name, words)}
    return client.post(PREVIEWS_URL, json=body)


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
        body[key] = _words(key, value)
    _ok(client.post(PROFILES_URL, json=body))


@given(parsers.parse('the job board "Remote OK" was imported with:'))
def given_imported(client: TestClient, state: ScenarioState, datatable: list[list[str]]) -> None:
    header, *rows = datatable
    state.remoteok = [dict(zip(header, values, strict=True)) for values in rows]
    _ok(client.post(f"/api/v1/job-boards/{state.remoteok_id}/imports"))


@given(
    parsers.parse('the job board "Remote OK" was imported again without the offer of "{company}"')
)
def given_imported_again(client: TestClient, state: ScenarioState, company: str) -> None:
    state.remoteok = [row for row in state.remoteok if row["company"] != company]
    clock = FixedClock(datetime.now(UTC) + LATER)
    cast(FastAPI, client.app).dependency_overrides[get_clock] = lambda: clock
    _ok(client.post(f"/api/v1/job-boards/{state.remoteok_id}/imports"))


@given(parsers.parse('an offer for "{company}" as "{title}"'))
def given_offer(client: TestClient, company: str, title: str) -> None:
    body = {"url": "https://jobs.example/hand", "company": company, "title": title}
    _ok(client.post(OFFERS_URL, json=body))


@given(parsers.parse('I discarded the offer of "{company}"'))
def given_discarded(client: TestClient, company: str) -> None:
    _ok(client.post(f"{OFFERS_URL}/{_offer_id(client, company)}/discard", json={}))


@given(parsers.parse('I promoted the offer of "{company}"'))
def given_promoted(client: TestClient, company: str) -> None:
    _ok(client.post(f"{OFFERS_URL}/{_offer_id(client, company)}/promotion", json={}))


@given(parsers.re(f"I previewed {PREVIEW}"))
def given_previewed(
    client: TestClient, state: ScenarioState, name: str, field_name: str, words: str
) -> None:
    state.filtered_before = _filtered(client)
    state.preview = _ok(_preview(client, _profile_id(client, name), field_name, words), 200)


# --- When ---


@when(parsers.re(f"I preview {PREVIEW}"))
def when_preview(
    client: TestClient, state: ScenarioState, name: str, field_name: str, words: str
) -> None:
    state.response = _preview(client, _profile_id(client, name), field_name, words)


@when(parsers.parse('I preview a nonexistent profile with the {field_name} "{words}"'))
def when_preview_nonexistent(
    client: TestClient, state: ScenarioState, field_name: str, words: str
) -> None:
    state.response = _preview(client, str(uuid7()), field_name, words)


@when(parsers.parse('I edit the profile "{name}" to have the {field_name} "{words}"'))
def when_edit(client: TestClient, name: str, field_name: str, words: str) -> None:
    body = {field_name: _words(field_name, words)}
    _ok(client.patch(f"{PROFILES_URL}/{_profile_id(client, name)}", json=body), 200)


@when(parsers.parse('I view the offer of "{company}"'))
def when_view(client: TestClient, state: ScenarioState, company: str) -> None:
    state.response = client.get(f"{OFFERS_URL}/{_offer_id(client, company)}")


# --- Then ---


@then(parsers.parse("{entering:d} offers would come into Pending and {leaving:d} would leave it"))
def then_pending(state: ScenarioState, entering: int, leaving: int) -> None:
    preview = _ok(state.last_response, 200)
    assert (preview["entering_pending"], preview["leaving_pending"]) == (entering, leaving)


@then("the offer is not filtered")
def then_not_filtered(state: ScenarioState) -> None:
    assert _ok(state.last_response, 200)["filtered"] is False


@then("the pending offers that came in and left match the preview")
def then_matches(client: TestClient, state: ScenarioState) -> None:
    assert state.preview is not None
    filtered_after = _filtered(client)
    entering = len(state.filtered_before - filtered_after)
    leaving = len(filtered_after - state.filtered_before)
    expected = (state.preview["entering_pending"], state.preview["leaving_pending"])
    assert (entering, leaving) == expected


@then(
    parsers.re(
        r"the change would have filtered (?P<promoted>\d+) offers? I promoted "
        r"and (?P<discarded>\d+) I discarded"
    )
)
def then_promoted_discarded(state: ScenarioState, promoted: str, discarded: str) -> None:
    preview = _ok(state.last_response, 200)
    counts = (preview["promoted_filtered"], preview["discarded_filtered"])
    assert counts == (int(promoted), int(discarded))


@then("it is rejected because the profile does not exist")
def then_not_found(state: ScenarioState) -> None:
    response = state.last_response
    assert (response.status_code, response.json()["type"]) == (404, "/problems/not-found")


@then("it is rejected as invalid")
def then_invalid(state: ScenarioState) -> None:
    response = state.last_response
    assert (response.status_code, response.json()["type"]) == (422, "/problems/validation-error")
