import re
from dataclasses import dataclass
from typing import Any
from uuid import uuid7

import httpx2
import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.bdd

scenarios("discovery/job_boards.feature")

URL = "/api/v1/job-boards"
TEMPLATE = "https://jobs.example/search?q={query}"

# `[^"]*` instead of parse's `{}`: an empty value must still match the step.
_NAME = r'"(?P<name>[^"]*)"'
_TEMPLATE = r'"(?P<template>[^"]*)"'
_SYNTAX = r'"(?P<syntax>[^"]*)"'
_FIELD = r'"(?P<field>[^"]*)"'
_VALUE = r'"(?P<value>[^"]*)"'


@dataclass
class ScenarioState:
    job_board_id: str | None = None
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


def _body(name: str) -> dict[str, str]:
    return {"name": name, "search_url_template": TEMPLATE, "syntax": "boolean"}


def _create(client: TestClient, state: ScenarioState, body: dict[str, Any]) -> None:
    state.response = client.post(URL, json=body)
    if state.response.status_code == 201:
        state.job_board_id = state.response.json()["id"]


def _read_job_board(client: TestClient, state: ScenarioState) -> dict[str, Any]:
    assert state.job_board_id is not None, "no job board in this scenario"
    response = client.get(f"{URL}/{state.job_board_id}")
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _update(client: TestClient, state: ScenarioState, body: dict[str, Any]) -> None:
    state.response = client.patch(f"{URL}/{state.job_board_id}", json=body)


def _assert_problem(state: ScenarioState, status: int, slug: str) -> None:
    response = state.last_response
    assert (response.status_code, response.json()["type"]) == (status, f"/problems/{slug}")


# --- Given ---


@given(parsers.parse('a job board named "{name}"'))
def given_job_board(client: TestClient, state: ScenarioState, name: str) -> None:
    response = client.post(URL, json=_body(name))
    assert response.status_code == 201, response.text
    state.job_board_id = response.json()["id"]


@given(parsers.parse("job boards named {names}"))
def given_job_boards(client: TestClient, names: str) -> None:
    for name in _quoted(names):
        response = client.post(URL, json=_body(name))
        assert response.status_code == 201, response.text


# --- When ---


@when("I create a job board with:")
def when_create_with(client: TestClient, state: ScenarioState, datatable: list[list[str]]) -> None:
    _create(client, state, dict(datatable))


@when(
    parsers.re(
        f"I create a job board named {_NAME} with template {_TEMPLATE} and syntax {_SYNTAX}$"
    )
)
def when_create(
    client: TestClient, state: ScenarioState, name: str, template: str, syntax: str
) -> None:
    body = {"name": name, "search_url_template": template, "syntax": syntax}
    _create(client, state, body)


@when("I view that job board")
def when_view(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(f"{URL}/{state.job_board_id}")


@when("I view a nonexistent job board")
def when_view_nonexistent(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(f"{URL}/{uuid7()}")


@when("I list the job boards")
def when_list(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(URL)


@when(parsers.re(f"I change its {_FIELD} to {_VALUE}$"))
def when_change(client: TestClient, state: ScenarioState, field: str, value: str) -> None:
    _update(client, state, {field: value})


@when(parsers.parse('I clear its "{field}"'))
def when_clear(client: TestClient, state: ScenarioState, field: str) -> None:
    _update(client, state, {field: None})


@when(parsers.parse('I change the "{field}" of a nonexistent job board to "{value}"'))
def when_change_nonexistent(
    client: TestClient, state: ScenarioState, field: str, value: str
) -> None:
    state.response = client.patch(f"{URL}/{uuid7()}", json={field: value})


@when("I delete that job board")
def when_delete(client: TestClient, state: ScenarioState) -> None:
    state.response = client.delete(f"{URL}/{state.job_board_id}")


@when("I delete a nonexistent job board")
def when_delete_nonexistent(client: TestClient, state: ScenarioState) -> None:
    state.response = client.delete(f"{URL}/{uuid7()}")


# --- Then ---


@then("the job board has:")
def then_job_board_has(
    client: TestClient, state: ScenarioState, datatable: list[list[str]]
) -> None:
    job_board = _read_job_board(client, state)
    assert {field: job_board[field] for field, _ in datatable} == dict(datatable)


@then(parsers.parse('its "{field}" is "{value}"'))
def then_field_is(client: TestClient, state: ScenarioState, field: str, value: str) -> None:
    assert _read_job_board(client, state)[field] == value


@then(parsers.parse('I see the job board "{name}"'))
def then_see_job_board(state: ScenarioState, name: str) -> None:
    response = state.last_response
    assert response.status_code == 200, response.text
    assert response.json()["name"] == name


@then("it is rejected as invalid")
def then_invalid(state: ScenarioState) -> None:
    _assert_problem(state, 422, "validation-error")


@then("it is rejected because the job board already exists")
def then_already_exists(state: ScenarioState) -> None:
    _assert_problem(state, 409, "already-exists")


@then("it is rejected because the job board does not exist")
def then_not_found(state: ScenarioState) -> None:
    _assert_problem(state, 404, "not-found")


@then(parsers.parse("the job boards are, in order: {names}"))
def then_job_boards_in_order(state: ScenarioState, names: str) -> None:
    response = state.last_response
    assert response.status_code == 200, response.text
    assert [item["name"] for item in response.json()["items"]] == _quoted(names)


@then(parsers.parse("there are {total:d} job boards in total"))
def then_total(state: ScenarioState, total: int) -> None:
    assert state.last_response.json()["total"] == total


@then("the job board no longer exists")
def then_no_longer_exists(client: TestClient, state: ScenarioState) -> None:
    assert state.last_response.status_code == 204, state.last_response.text
    assert client.get(f"{URL}/{state.job_board_id}").status_code == 404
