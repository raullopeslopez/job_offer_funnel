import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, cast
from uuid import UUID, uuid7

import httpx2
import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when
from support.factories import ApplicationDetails, make_application

from funnel.core.config import Settings
from funnel.modules.applications.domain import Channel, Outcome, Priority, Stage

pytestmark = pytest.mark.bdd

scenarios("applications/manage_applications.feature")

# `[^"]*` instead of parse's `{}`: an empty value must still match the step.
_COMPANY = r'"(?P<company>[^"]*)"'
_ROLE = r'"(?P<role>[^"]*)"'
_CHANNEL = r'"(?P<channel>[^"]*)"'
_FIELD = r'"(?P<field>[^"]*)"'
_VALUE = r'"(?P<value>[^"]*)"'
_CREATE = f"I create an application for {_COMPANY} as {_ROLE} via {_CHANNEL}"


@dataclass
class ScenarioState:
    companies: dict[str, str] = field(default_factory=dict)
    application_id: UUID | str | None = None
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


def _company_id(state: ScenarioState, name: str) -> UUID:
    return UUID(state.companies[name])


def _api_field(state: ScenarioState, name: str, value: str) -> tuple[str, str]:
    """Translate a spec field (`company` is a name) to its API field and value."""
    if name == "company":
        return "company_id", state.companies[value]
    return name, value


def _create(client: TestClient, state: ScenarioState, body: dict[str, Any]) -> None:
    state.response = client.post("/api/v1/applications", json=body)
    if state.response.status_code == 201:
        state.application_id = state.response.json()["id"]


def _required_body(state: ScenarioState, company: str, role: str, channel: str) -> dict[str, Any]:
    return {"company_id": state.companies[company], "role": role, "channel": channel}


def _update(client: TestClient, state: ScenarioState, body: dict[str, Any]) -> None:
    state.response = client.patch(f"/api/v1/applications/{state.application_id}", json=body)


def _read_application(client: TestClient, state: ScenarioState) -> dict[str, Any]:
    response = client.get(f"/api/v1/applications/{state.application_id}")
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def _list(client: TestClient, params: dict[str, str | int]) -> httpx2.Response:
    return client.get("/api/v1/applications", params=params)


def _move(client: TestClient, state: ScenarioState, body: dict[str, Any]) -> None:
    response = client.post(f"/api/v1/applications/{state.application_id}/transitions", json=body)
    assert response.status_code == 201, response.text


def _assert_problem(state: ScenarioState, status: int, slug: str) -> None:
    response = state.last_response
    assert (response.status_code, response.json()["type"]) == (status, f"/problems/{slug}")


# --- Given ---


@given(parsers.parse('a company named "{name}"'))
def given_company(client: TestClient, state: ScenarioState, name: str) -> None:
    response = client.post("/api/v1/companies", json={"name": name})
    assert response.status_code == 201, response.text
    state.companies[name] = response.json()["id"]


@given(parsers.re(f"an application for {_COMPANY} as {_ROLE}$"))
def given_application(settings: Settings, state: ScenarioState, company: str, role: str) -> None:
    details = ApplicationDetails(company_id=_company_id(state, company), role=role)
    state.application_id = make_application(
        settings.database_url, stage=Stage.EVALUATED, details=details
    )


@given(
    parsers.parse(
        'an application for "{company}" as "{role}" with priority "{priority}", '
        'url "{url}" and notes "{notes}"'
    )
)
def given_application_with_optionals(
    settings: Settings,
    state: ScenarioState,
    company: str,
    role: str,
    priority: str,
    url: str,
    notes: str,
) -> None:
    details = ApplicationDetails(
        company_id=_company_id(state, company),
        role=role,
        priority=Priority(priority),
        url=url,
        notes=notes,
    )
    state.application_id = make_application(
        settings.database_url, stage=Stage.EVALUATED, details=details
    )


@given(parsers.parse('an application for "{company}" as "{role}" in stage "{stage}" since {day}'))
def given_application_since(
    settings: Settings, state: ScenarioState, company: str, role: str, stage: str, day: str
) -> None:
    details = ApplicationDetails(company_id=_company_id(state, company), role=role)
    state.application_id = make_application(
        settings.database_url,
        stage=Stage(stage),
        entered_on=date.fromisoformat(day),
        details=details,
    )


@given(parsers.parse('it was moved to stage "{stage}" on {day}'))
def given_moved(client: TestClient, state: ScenarioState, stage: str, day: str) -> None:
    _move(client, state, {"to_stage": stage, "occurred_on": day})


@given(parsers.parse('it was closed as "{outcome}" on {day}'))
def given_closed(client: TestClient, state: ScenarioState, outcome: str, day: str) -> None:
    _move(client, state, {"outcome": outcome, "occurred_on": day})


@given(parsers.parse('applications for "{company}" as {roles}, created in that order'))
def given_applications(settings: Settings, state: ScenarioState, company: str, roles: str) -> None:
    company_id = _company_id(state, company)
    for role in _quoted(roles):
        details = ApplicationDetails(company_id=company_id, role=role)
        make_application(settings.database_url, stage=Stage.EVALUATED, details=details)


@given(parsers.parse('these applications for "{company}", created in this order:'))
def given_these_applications(
    settings: Settings, state: ScenarioState, company: str, datatable: list[list[str]]
) -> None:
    header, *rows = datatable
    company_id = _company_id(state, company)
    for row in (dict(zip(header, values, strict=True)) for values in rows):
        details = ApplicationDetails(
            company_id=company_id, role=row["role"], channel=Channel(row["channel"])
        )
        make_application(
            settings.database_url,
            stage=Stage(row["stage"]),
            outcome=Outcome(row["outcome"]) if row["outcome"] else None,
            details=details,
        )


# --- When ---


@when("I create an application with:")
def when_create_with(client: TestClient, state: ScenarioState, datatable: list[list[str]]) -> None:
    body = dict(_api_field(state, name, value) for name, value in datatable)
    _create(client, state, body)


@when(parsers.re(f"{_CREATE}$"))
def when_create(
    client: TestClient, state: ScenarioState, company: str, role: str, channel: str
) -> None:
    _create(client, state, _required_body(state, company, role, channel))


@when(parsers.re(f'{_CREATE} in stage "(?P<stage>[^"]*)"$'))
def when_create_in_stage(
    client: TestClient, state: ScenarioState, company: str, role: str, channel: str, stage: str
) -> None:
    body = _required_body(state, company, role, channel) | {"stage": stage}
    _create(client, state, body)


@when(parsers.re(f'{_CREATE} in stage "(?P<stage>[^"]*)" on (?P<day>[0-9-]+)$'))
def when_create_in_stage_on(
    client: TestClient,
    state: ScenarioState,
    company: str,
    role: str,
    channel: str,
    stage: str,
    day: str,
) -> None:
    body = _required_body(state, company, role, channel) | {"stage": stage, "occurred_on": day}
    _create(client, state, body)


@when(parsers.re(f"{_CREATE} with {_FIELD} set to {_VALUE}$"))
def when_create_with_field(
    client: TestClient,
    state: ScenarioState,
    company: str,
    role: str,
    channel: str,
    field: str,
    value: str,
) -> None:
    body = _required_body(state, company, role, channel) | {field: value}
    _create(client, state, body)


@when("I create an application for a nonexistent company")
def when_create_for_nonexistent_company(client: TestClient, state: ScenarioState) -> None:
    body = {"company_id": str(uuid7()), "role": "Backend Engineer", "channel": "portal"}
    _create(client, state, body)


@when(parsers.re(f"I change its {_FIELD} to {_VALUE}$"))
def when_change(client: TestClient, state: ScenarioState, field: str, value: str) -> None:
    _update(client, state, dict([_api_field(state, field, value)]))


@when(parsers.parse('I clear its "{field}"'))
def when_clear(client: TestClient, state: ScenarioState, field: str) -> None:
    name = "company_id" if field == "company" else field
    _update(client, state, {name: None})


@when("I change its company to a nonexistent company")
def when_change_to_nonexistent_company(client: TestClient, state: ScenarioState) -> None:
    _update(client, state, {"company_id": str(uuid7())})


@when(parsers.parse('I change the "{field}" of a nonexistent application to "{value}"'))
def when_change_nonexistent(
    client: TestClient, state: ScenarioState, field: str, value: str
) -> None:
    state.application_id = uuid7()
    _update(client, state, {field: value})


@when("I view that application")
def when_view(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(f"/api/v1/applications/{state.application_id}")


@when("I view a nonexistent application")
def when_view_nonexistent(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(f"/api/v1/applications/{uuid7()}")


@when("I list the applications")
def when_list(client: TestClient, state: ScenarioState) -> None:
    state.response = _list(client, {})


@when(parsers.parse('I list the applications filtered by "{filters}"'))
def when_list_filtered(client: TestClient, state: ScenarioState, filters: str) -> None:
    params = dict(item.strip().split("=") for item in filters.split(","))
    state.response = _list(client, cast(dict[str, str | int], params))


@when(parsers.parse("I list the applications with limit {limit:d} and offset {offset:d}"))
def when_list_page(client: TestClient, state: ScenarioState, limit: int, offset: int) -> None:
    state.response = _list(client, {"limit": limit, "offset": offset})


# --- Then ---


@then("the application has:")
def then_application_has(
    client: TestClient, state: ScenarioState, datatable: list[list[str]]
) -> None:
    expected = dict(_api_field(state, name, value) for name, value in datatable)
    application = _read_application(client, state)
    assert {name: application[name] for name in expected} == expected


@then("the application has no priority, url or notes")
def then_no_optionals(client: TestClient, state: ScenarioState) -> None:
    application = _read_application(client, state)
    assert (application["priority"], application["url"], application["notes"]) == (None,) * 3


@then(parsers.re(r"the application has no (?P<field>\w+)$"))
def then_no_field(client: TestClient, state: ScenarioState, field: str) -> None:
    assert state.last_response.status_code == 200, state.last_response.text
    assert _read_application(client, state)[field] is None


@then(parsers.parse('its "{field}" is "{value}"'))
def then_field_is(client: TestClient, state: ScenarioState, field: str, value: str) -> None:
    assert state.last_response.status_code == 200, state.last_response.text
    name, expected = _api_field(state, field, value)
    assert _read_application(client, state)[name] == expected


@then(parsers.parse('the application is in stage "{stage}" and still open'))
def then_in_stage_and_open(client: TestClient, state: ScenarioState, stage: str) -> None:
    application = _read_application(client, state)
    assert (application["stage"], application["outcome"]) == (stage, None)


@then(parsers.parse('the application is closed as "{outcome}" with reached stage "{stage}"'))
def then_closed(client: TestClient, state: ScenarioState, outcome: str, stage: str) -> None:
    application = _read_application(client, state)
    assert (application["stage"], application["outcome"]) == (stage, outcome)


@then("its history is:")
def then_history_is(client: TestClient, state: ScenarioState, datatable: list[list[str]]) -> None:
    header, *rows = datatable
    expected = [dict(zip(header, values, strict=True)) for values in rows]
    history = [
        {
            "stage": transition["to_stage"],
            "outcome": transition["outcome"] or "",
            "occurred_on": transition["occurred_on"],
        }
        for transition in _read_application(client, state)["transitions"]
    ]
    assert history == expected


@then("it is rejected as invalid")
def then_invalid(state: ScenarioState) -> None:
    _assert_problem(state, 422, "validation-error")


@then("it is rejected because the date is not valid")
def then_invalid_date(state: ScenarioState) -> None:
    _assert_problem(state, 422, "invalid-transition-date")


@then("it is rejected because the company does not exist")
def then_unknown_company(state: ScenarioState) -> None:
    _assert_problem(state, 422, "unknown-company")


@then("it is rejected because the application does not exist")
def then_not_found(state: ScenarioState) -> None:
    _assert_problem(state, 404, "not-found")


@then(parsers.parse("there are {total:d} applications in total"))
def then_total(client: TestClient, total: int) -> None:
    response = _list(client, {})
    assert response.status_code == 200, response.text
    assert response.json()["total"] == total


@then(parsers.re(r"the applications are, in order:(?P<roles>.*)$"))
def then_roles_in_order(state: ScenarioState, roles: str) -> None:
    response = state.last_response
    assert response.status_code == 200, response.text
    assert [item["role"] for item in response.json()["items"]] == _quoted(roles)


@then("there are no applications")
def then_no_applications(state: ScenarioState) -> None:
    response = state.last_response
    assert response.status_code == 200, response.text
    assert response.json()["items"] == []
