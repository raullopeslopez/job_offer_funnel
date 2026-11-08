import re
from dataclasses import dataclass
from typing import Any
from uuid import uuid7

import httpx2
import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.bdd

scenarios("discovery/search_profiles.feature")

URL = "/api/v1/search-profiles"
LIST_FIELDS = frozenset({"titles", "keywords", "excluded_keywords", "work_modes"})

# `[^"]*` instead of parse's `{}`: an empty value must still match the step.
_NAME = r'"(?P<name>[^"]*)"'
_TITLES = r'"(?P<titles>[^"]*)"'
_FIELD = r'"(?P<field>[^"]*)"'
_VALUE = r'"(?P<value>[^"]*)"'


@dataclass
class ScenarioState:
    profile_id: str | None = None
    response: httpx2.Response | None = None

    @property
    def last_response(self) -> httpx2.Response:
        assert self.response is not None, "no request was made in this scenario"
        return self.response


@pytest.fixture
def state() -> ScenarioState:
    return ScenarioState()


def _quoted(text: str) -> list[str]:
    return re.findall(r'"([^"]*)"', text)


def _api_value(field: str, value: str) -> object:
    """Spec values are text; list fields are separated by commas and the spaces around them.

    The spaces at both ends are kept, so the API trimming them is still tested.
    """
    if field not in LIST_FIELDS:
        return value
    return re.split(r"\s*,\s*", value) if value else []


def _spec_value(field: str, value: object) -> object:
    if field in LIST_FIELDS:
        assert isinstance(value, list)
        return ", ".join(value)
    return value


def _create(client: TestClient, state: ScenarioState, body: dict[str, Any]) -> None:
    state.response = client.post(URL, json=body)
    if state.response.status_code == 201:
        state.profile_id = state.response.json()["id"]


def _given(client: TestClient, state: ScenarioState, body: dict[str, Any]) -> None:
    response = client.post(URL, json=body)
    assert response.status_code == 201, response.text
    state.profile_id = response.json()["id"]


def _read_profile(client: TestClient, state: ScenarioState) -> dict[str, Any]:
    assert state.profile_id is not None, "no search profile in this scenario"
    response = client.get(f"{URL}/{state.profile_id}")
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _update(client: TestClient, state: ScenarioState, body: dict[str, Any]) -> None:
    state.response = client.patch(f"{URL}/{state.profile_id}", json=body)


def _assert_problem(state: ScenarioState, status: int, slug: str) -> None:
    response = state.last_response
    assert (response.status_code, response.json()["type"]) == (status, f"/problems/{slug}")


# --- Given ---


@given(parsers.re(f"a search profile named {_NAME}$"))
def given_profile(client: TestClient, state: ScenarioState, name: str) -> None:
    _given(client, state, {"name": name, "titles": ["Backend Engineer"]})


@given(parsers.parse("search profiles named {names}"))
def given_profiles(client: TestClient, names: str) -> None:
    for name in _quoted(names):
        response = client.post(URL, json={"name": name, "titles": ["Backend Engineer"]})
        assert response.status_code == 201, response.text


@given(
    parsers.parse(
        'a search profile named "{name}" with keywords "{keywords}", excluded keywords '
        '"{excluded}", location "{location}" and work modes "{work_modes}"'
    )
)
def given_full_profile(
    client: TestClient,
    state: ScenarioState,
    name: str,
    keywords: str,
    excluded: str,
    location: str,
    work_modes: str,
) -> None:
    body = {
        "name": name,
        "titles": ["Backend Engineer"],
        "keywords": _api_value("keywords", keywords),
        "excluded_keywords": _api_value("excluded_keywords", excluded),
        "location": location,
        "work_modes": _api_value("work_modes", work_modes),
    }
    _given(client, state, body)


# --- When ---


@when("I create a search profile with:")
def when_create_with(client: TestClient, state: ScenarioState, datatable: list[list[str]]) -> None:
    _create(client, state, {field: _api_value(field, value) for field, value in datatable})


@when(parsers.re(f"I create a search profile named {_NAME} with titles {_TITLES}$"))
def when_create(client: TestClient, state: ScenarioState, name: str, titles: str) -> None:
    _create(client, state, {"name": name, "titles": _api_value("titles", titles)})


@when(
    parsers.re(
        f"I create a search profile named {_NAME} with titles {_TITLES} "
        f"and {_FIELD} set to {_VALUE}$"
    )
)
def when_create_with_field(
    client: TestClient, state: ScenarioState, name: str, titles: str, field: str, value: str
) -> None:
    body = {"name": name, "titles": _api_value("titles", titles), field: _api_value(field, value)}
    _create(client, state, body)


@when("I view that search profile")
def when_view(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(f"{URL}/{state.profile_id}")


@when("I view a nonexistent search profile")
def when_view_nonexistent(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(f"{URL}/{uuid7()}")


@when("I list the search profiles")
def when_list(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(URL)


@when(parsers.re(f"I change its {_FIELD} to {_VALUE}$"))
def when_change(client: TestClient, state: ScenarioState, field: str, value: str) -> None:
    _update(client, state, {field: _api_value(field, value)})


@when(parsers.parse('I clear its "{field}"'))
def when_clear(client: TestClient, state: ScenarioState, field: str) -> None:
    _update(client, state, {field: [] if field in LIST_FIELDS else None})


@when(parsers.parse('I change the "{field}" of a nonexistent search profile to "{value}"'))
def when_change_nonexistent(
    client: TestClient, state: ScenarioState, field: str, value: str
) -> None:
    state.response = client.patch(f"{URL}/{uuid7()}", json={field: _api_value(field, value)})


@when("I delete that search profile")
def when_delete(client: TestClient, state: ScenarioState) -> None:
    state.response = client.delete(f"{URL}/{state.profile_id}")


@when("I delete a nonexistent search profile")
def when_delete_nonexistent(client: TestClient, state: ScenarioState) -> None:
    state.response = client.delete(f"{URL}/{uuid7()}")


# --- Then ---


@then("the search profile has:")
def then_profile_has(client: TestClient, state: ScenarioState, datatable: list[list[str]]) -> None:
    profile = _read_profile(client, state)
    actual = {field: _spec_value(field, profile[field]) for field, _ in datatable}
    assert actual == dict(datatable)


@then(parsers.re(r"the search profile has no (?P<field>\w+)$"))
def then_profile_has_no(client: TestClient, state: ScenarioState, field: str) -> None:
    assert state.last_response.status_code in {200, 201}, state.last_response.text
    assert _read_profile(client, state)[field] in ([], None)


@then(parsers.parse('its "{field}" is "{value}"'))
def then_field_is(client: TestClient, state: ScenarioState, field: str, value: str) -> None:
    assert state.last_response.status_code == 200, state.last_response.text
    assert _spec_value(field, _read_profile(client, state)[field]) == value


@then(parsers.parse('I see the search profile "{name}"'))
def then_see_profile(state: ScenarioState, name: str) -> None:
    response = state.last_response
    assert response.status_code == 200, response.text
    assert response.json()["name"] == name


@then("it is rejected as invalid")
def then_invalid(state: ScenarioState) -> None:
    _assert_problem(state, 422, "validation-error")


@then("it is rejected because the search profile already exists")
def then_already_exists(state: ScenarioState) -> None:
    _assert_problem(state, 409, "already-exists")


@then("it is rejected because the search profile does not exist")
def then_not_found(state: ScenarioState) -> None:
    _assert_problem(state, 404, "not-found")


@then(parsers.parse("the search profiles are, in order: {names}"))
def then_profiles_in_order(state: ScenarioState, names: str) -> None:
    response = state.last_response
    assert response.status_code == 200, response.text
    assert [item["name"] for item in response.json()["items"]] == _quoted(names)


@then(parsers.parse("there are {total:d} search profiles in total"))
def then_total(state: ScenarioState, total: int) -> None:
    assert state.last_response.json()["total"] == total


@then("the search profile no longer exists")
def then_no_longer_exists(client: TestClient, state: ScenarioState) -> None:
    assert state.last_response.status_code == 204, state.last_response.text
    assert client.get(f"{URL}/{state.profile_id}").status_code == 404
