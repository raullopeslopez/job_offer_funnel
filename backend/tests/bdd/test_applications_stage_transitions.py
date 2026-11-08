from dataclasses import dataclass
from datetime import date
from typing import Any, cast
from uuid import UUID, uuid7

import httpx2
import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when
from support.factories import make_application

from funnel.core.config import Settings
from funnel.modules.applications.domain import Outcome, Stage

pytestmark = pytest.mark.bdd

scenarios("applications/stage_transitions.feature")


@dataclass
class ScenarioState:
    application_id: UUID | None = None
    response: httpx2.Response | None = None

    @property
    def last_response(self) -> httpx2.Response:
        assert self.response is not None, "no request was made in this scenario"
        return self.response


@pytest.fixture
def state() -> ScenarioState:
    return ScenarioState()


def _post_transition(
    client: TestClient, application_id: UUID | None, body: dict[str, Any]
) -> httpx2.Response:
    return client.post(f"/api/v1/applications/{application_id}/transitions", json=body)


def _read_application(client: TestClient, state: ScenarioState) -> dict[str, Any]:
    response = client.get(f"/api/v1/applications/{state.application_id}")
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def _read_history(client: TestClient, state: ScenarioState) -> list[dict[str, Any]]:
    response = client.get(f"/api/v1/applications/{state.application_id}/transitions")
    assert response.status_code == 200, response.text
    return cast(list[dict[str, Any]], response.json())


def _assert_problem(state: ScenarioState, status: int, slug: str) -> None:
    response = state.last_response
    assert (response.status_code, response.json()["type"]) == (status, f"/problems/{slug}")


# --- Given ---


@given(parsers.parse('an application in stage "{stage}"'))
def given_application_in_stage(settings: Settings, state: ScenarioState, stage: str) -> None:
    state.application_id = make_application(settings.database_url, stage=Stage(stage))


@given(parsers.parse('an application closed as "{outcome}" with reached stage "{stage}"'))
def given_closed_application(
    settings: Settings, state: ScenarioState, outcome: str, stage: str
) -> None:
    state.application_id = make_application(
        settings.database_url, stage=Stage(stage), outcome=Outcome(outcome)
    )


@given(parsers.parse('an application that moved to stage "{stage}" on {day}'))
def given_application_moved_on(
    settings: Settings, state: ScenarioState, stage: str, day: str
) -> None:
    state.application_id = make_application(
        settings.database_url, stage=Stage(stage), entered_on=date.fromisoformat(day)
    )


@given(parsers.parse('I moved it to stage "{stage}" on {day} with the note "{note}"'))
def given_moved_with_note(
    client: TestClient, state: ScenarioState, stage: str, day: str, note: str
) -> None:
    body = {"to_stage": stage, "occurred_on": day, "note": note}
    response = _post_transition(client, state.application_id, body)
    assert response.status_code == 201, response.text


@given(parsers.parse('I closed it as "{outcome}" on {day}'))
def given_closed_on(client: TestClient, state: ScenarioState, outcome: str, day: str) -> None:
    response = _post_transition(
        client, state.application_id, {"outcome": outcome, "occurred_on": day}
    )
    assert response.status_code == 201, response.text


# --- When ---


@when(parsers.parse('I move it to stage "{stage}"'))
def when_move(client: TestClient, state: ScenarioState, stage: str) -> None:
    state.response = _post_transition(client, state.application_id, {"to_stage": stage})


@when(parsers.parse('I move it to stage "{stage}" on {day}'))
def when_move_on(client: TestClient, state: ScenarioState, stage: str, day: str) -> None:
    body = {"to_stage": stage, "occurred_on": day}
    state.response = _post_transition(client, state.application_id, body)


@when(parsers.parse('I close it as "{outcome}"'))
def when_close(client: TestClient, state: ScenarioState, outcome: str) -> None:
    state.response = _post_transition(client, state.application_id, {"outcome": outcome})


@when("I view its transition history")
def when_view_history(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(f"/api/v1/applications/{state.application_id}/transitions")


@when(parsers.parse('I move a nonexistent application to stage "{stage}"'))
def when_move_nonexistent(client: TestClient, state: ScenarioState, stage: str) -> None:
    state.response = _post_transition(client, uuid7(), {"to_stage": stage})


@when("I undo its last transition")
def when_undo(client: TestClient, state: ScenarioState) -> None:
    url = f"/api/v1/applications/{state.application_id}/transitions/latest"
    state.response = client.delete(url)


@when("I undo the last transition of a nonexistent application")
def when_undo_nonexistent(client: TestClient, state: ScenarioState) -> None:
    state.response = client.delete(f"/api/v1/applications/{uuid7()}/transitions/latest")


# --- Then ---


@then(parsers.parse('the application is in stage "{stage}" and still open'))
def then_in_stage_and_open(client: TestClient, state: ScenarioState, stage: str) -> None:
    application = _read_application(client, state)
    assert (application["stage"], application["outcome"]) == (stage, None)


@then(parsers.parse('the application is still in stage "{stage}"'))
def then_still_in_stage(client: TestClient, state: ScenarioState, stage: str) -> None:
    assert _read_application(client, state)["stage"] == stage


@then(parsers.parse('the application is still in stage "{stage}" and open'))
def then_still_in_stage_and_open(client: TestClient, state: ScenarioState, stage: str) -> None:
    application = _read_application(client, state)
    assert (application["stage"], application["outcome"]) == (stage, None)


@then(parsers.parse('the application is closed as "{outcome}" with reached stage "{stage}"'))
def then_closed(client: TestClient, state: ScenarioState, outcome: str, stage: str) -> None:
    application = _read_application(client, state)
    assert (application["stage"], application["outcome"]) == (stage, outcome)


@then(parsers.parse("the latest transition is dated {day}"))
def then_latest_dated(client: TestClient, state: ScenarioState, day: str) -> None:
    assert _read_history(client, state)[-1]["occurred_on"] == day


@then("it is rejected as an invalid transition")
def then_invalid_transition(state: ScenarioState) -> None:
    _assert_problem(state, 409, "invalid-transition")


@then("it is rejected as an invalid date")
def then_invalid_date(state: ScenarioState) -> None:
    _assert_problem(state, 422, "invalid-transition-date")


@then("it is rejected because the application does not exist")
def then_not_found(state: ScenarioState) -> None:
    _assert_problem(state, 404, "not-found")


@then("the history is:")
def then_history_is(state: ScenarioState, datatable: list[list[str]]) -> None:
    header, *rows = datatable
    expected = [
        {
            "from_stage": row["from"] or None,
            "to_stage": row["to"],
            "outcome": row["outcome"] or None,
            "occurred_on": row["date"],
            "note": row["note"] or None,
        }
        for row in (dict(zip(header, values, strict=True)) for values in rows)
    ]
    assert state.last_response.json() == expected
