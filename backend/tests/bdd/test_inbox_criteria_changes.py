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

scenarios("inbox/criteria_changes.feature")

OFFERS_URL = "/api/v1/offers"
PROFILES_URL = "/api/v1/search-profiles"
CHANGES_URL = "/api/v1/criteria-changes"
LIST_FIELDS = frozenset({"titles", "keywords", "excluded_keywords", "work_modes"})
CHANGE = r'the profile "(?P<name>[^"]+)" to have the (?P<field_name>\w+) "(?P<words>[^"]*)"'

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


def _ok(response: httpx2.Response, status: int = 201) -> Any:
    assert response.status_code == status, response.text
    return response.json() if response.content else {}


def _words(field_name: str, words: str) -> list[str] | str:
    if field_name not in LIST_FIELDS:
        return words
    return re.split(r"\s*,\s*", words) if words else []


def _profile(client: TestClient, name: str) -> dict[str, Any]:
    items = _ok(client.get(PROFILES_URL), 200)["items"]
    profile: dict[str, Any] = next(p for p in items if p["name"] == name)
    return profile


def _offer_id(client: TestClient, company: str) -> str:
    items = _ok(client.get(OFFERS_URL, params={"limit": "100"}), 200)["items"]
    offer_id: str = next(o["id"] for o in items if o["company"] == company)
    return offer_id


def _changes(client: TestClient) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = _ok(client.get(CHANGES_URL), 200)["items"]
    return items


def _change(client: TestClient, name: str, field_name: str, words: str) -> httpx2.Response:
    body = {
        "search_profile_id": _profile(client, name)["id"],
        field_name: _words(field_name, words),
    }
    return client.post(CHANGES_URL, json=body)


def _undo(client: TestClient, change_id: str) -> httpx2.Response:
    return client.delete(f"{CHANGES_URL}/{change_id}")


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


@given(parsers.re(f"I changed {CHANGE}$"))
def given_changed(client: TestClient, name: str, field_name: str, words: str) -> None:
    _ok(_change(client, name, field_name, words))


# --- When ---


@when(parsers.re(f"I change {CHANGE}$"))
def when_change(
    client: TestClient, state: ScenarioState, name: str, field_name: str, words: str
) -> None:
    state.response = _change(client, name, field_name, words)


@when(
    parsers.parse(
        'I change the profile "{name}" to have the {field_name} "{words}" '
        'from the offer of "{company}"'
    )
)
def when_change_from_offer(  # noqa: PLR0913, PLR0917  # pytest-bdd passes each part
    client: TestClient, state: ScenarioState, name: str, field_name: str, words: str, company: str
) -> None:
    body = {
        "search_profile_id": _profile(client, name)["id"],
        field_name: _words(field_name, words),
        "offer_id": _offer_id(client, company),
    }
    state.response = client.post(CHANGES_URL, json=body)


@when(
    parsers.parse(
        'I change the profile "{name}" to have the titles "{titles}" and the keywords "{keywords}"'
    )
)
def when_change_two(
    client: TestClient, state: ScenarioState, name: str, titles: str, keywords: str
) -> None:
    body = {
        "search_profile_id": _profile(client, name)["id"],
        "titles": _words("titles", titles),
        "keywords": _words("keywords", keywords),
    }
    state.response = client.post(CHANGES_URL, json=body)


@when(parsers.parse('I change a nonexistent profile to have the {field_name} "{words}"'))
def when_change_nonexistent(
    client: TestClient, state: ScenarioState, field_name: str, words: str
) -> None:
    body = {"search_profile_id": str(uuid7()), field_name: _words(field_name, words)}
    state.response = client.post(CHANGES_URL, json=body)


@when("I list the changes")
def when_list(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(CHANGES_URL)


@when("I undo the latest change")
def when_undo_latest(client: TestClient, state: ScenarioState) -> None:
    state.response = _undo(client, _changes(client)[0]["id"])


@when(parsers.parse("I undo the change of the {rule}"))
def when_undo_rule(client: TestClient, state: ScenarioState, rule: str) -> None:
    change = next(c for c in _changes(client) if c["rule"] == rule)
    state.response = _undo(client, change["id"])


@when(parsers.parse('I undo the change of the {rule} to "{words}"'))
def when_undo_to(client: TestClient, state: ScenarioState, rule: str, words: str) -> None:
    after = _words(rule, words)
    change = next(c for c in _changes(client) if c["rule"] == rule and c["after"] == after)
    state.response = _undo(client, change["id"])


@when("I undo a nonexistent change")
def when_undo_nonexistent(client: TestClient, state: ScenarioState) -> None:
    state.response = _undo(client, str(uuid7()))


# --- Then ---


@then(parsers.parse('the profile "{name}" has the {field_name} "{words}"'))
def then_profile_has(client: TestClient, name: str, field_name: str, words: str) -> None:
    assert _profile(client, name)[field_name] == _words(field_name, words)


@then(
    parsers.re(
        r'the log has 1 change, on the (?P<rule>\w+) of "(?P<name>[^"]+)" '
        r'from "(?P<before>[^"]*)" to "(?P<after>[^"]*)", '
        r"that took (?P<leaving>\d+) offers? out of Pending"
    )
)
def then_logged(  # noqa: PLR0913, PLR0917  # pytest-bdd passes each part
    client: TestClient, rule: str, name: str, before: str, after: str, leaving: str
) -> None:
    [change] = _changes(client)
    found = (
        change["rule"],
        change["search_profile_name"],
        change["before"],
        change["after"],
        change["leaving_pending"],
    )
    assert found == (rule, name, _words(rule, before), _words(rule, after), int(leaving))


@then(parsers.parse('the latest change came from the offer of "{company}"'))
def then_from_offer(client: TestClient, company: str) -> None:
    assert _changes(client)[0]["offer_id"] == _offer_id(client, company)


@then(parsers.re(r"the changes are, in order: (?P<rules>.+)"))
def then_order(state: ScenarioState, rules: str) -> None:
    items = _ok(state.last_response, 200)["items"]
    assert [item["rule"] for item in items] == re.findall(r'"([^"]*)"', rules)


@then("the log is empty")
def then_empty(client: TestClient) -> None:
    assert _changes(client) == []


@then("it is rejected as invalid")
def then_invalid(state: ScenarioState) -> None:
    response = state.last_response
    assert (response.status_code, response.json()["type"]) == (422, "/problems/validation-error")


@then("it is rejected because it does not exist")
def then_not_found(state: ScenarioState) -> None:
    response = state.last_response
    assert (response.status_code, response.json()["type"]) == (404, "/problems/not-found")


@then("it is rejected because the rule changed since")
def then_changed_since(state: ScenarioState) -> None:
    response = state.last_response
    assert (response.status_code, response.json()["type"]) == (409, "/problems/rule-changed-since")
