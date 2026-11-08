import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid7

import httpx2
import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when
from support.factories import ApplicationDetails, make_application

from funnel.core.config import Settings
from funnel.modules.applications.domain import Stage

pytestmark = pytest.mark.bdd

scenarios("companies/manage_companies.feature")

# `[^"]*` instead of parse's `{}`: an empty name must still match the step.
_NAME = r'"(?P<name>[^"]*)"'
_WEBSITE = r'"(?P<website>[^"]*)"'
_FIELD = r'"(?P<field>[^"]*)"'
_VALUE = r'"(?P<value>[^"]*)"'


@dataclass
class ScenarioState:
    response: httpx2.Response | None = None
    company_id: str | None = None

    @property
    def last_response(self) -> httpx2.Response:
        assert self.response is not None, "no request was made in this scenario"
        return self.response


@pytest.fixture
def state() -> ScenarioState:
    return ScenarioState()


def _quoted(text: str) -> list[str]:
    return re.findall(r'"([^"]*)"', text)


def _create(client: TestClient, body: dict[str, Any]) -> httpx2.Response:
    return client.post("/api/v1/companies", json=body)


def _create_in_scenario(client: TestClient, state: ScenarioState, body: dict[str, Any]) -> None:
    state.response = _create(client, body)
    if state.response.status_code == 201:
        state.company_id = state.response.json()["id"]


def _given_company(client: TestClient, state: ScenarioState, body: dict[str, Any]) -> None:
    response = _create(client, body)
    assert response.status_code == 201, response.text
    state.company_id = response.json()["id"]


def _read_company(client: TestClient, state: ScenarioState) -> dict[str, Any]:
    assert state.company_id is not None, "no company in this scenario"
    response = client.get(f"/api/v1/companies/{state.company_id}")
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _update(client: TestClient, state: ScenarioState, body: dict[str, Any]) -> None:
    state.response = client.patch(f"/api/v1/companies/{state.company_id}", json=body)


def _assert_problem(state: ScenarioState, status: int, slug: str) -> None:
    response = state.last_response
    assert (response.status_code, response.json()["type"]) == (status, f"/problems/{slug}")


# --- Given ---


@given(parsers.re(f"a company named {_NAME}$"))
def given_company(client: TestClient, state: ScenarioState, name: str) -> None:
    _given_company(client, state, {"name": name})


@given(parsers.re(f"a company named {_NAME} with website {_WEBSITE}$"))
def given_company_with_website(
    client: TestClient, state: ScenarioState, name: str, website: str
) -> None:
    _given_company(client, state, {"name": name, "website": website})


@given(parsers.parse("companies named {names}"))
def given_companies(client: TestClient, names: str) -> None:
    for name in _quoted(names):
        response = _create(client, {"name": name})
        assert response.status_code == 201, response.text


@given("the company has an application")
def given_company_has_application(settings: Settings, state: ScenarioState) -> None:
    assert state.company_id is not None, "no company in this scenario"
    details = ApplicationDetails(company_id=UUID(state.company_id))
    make_application(settings.database_url, stage=Stage.EVALUATED, details=details)


# --- When ---


@when(parsers.re(f"I create a company named {_NAME}$"))
def when_create(client: TestClient, state: ScenarioState, name: str) -> None:
    _create_in_scenario(client, state, {"name": name})


@when(parsers.re(f"I create a company named {_NAME} with website {_WEBSITE}$"))
def when_create_with_website(
    client: TestClient, state: ScenarioState, name: str, website: str
) -> None:
    _create_in_scenario(client, state, {"name": name, "website": website})


@when(parsers.re(f"I change its {_FIELD} to {_VALUE}$"))
def when_change(client: TestClient, state: ScenarioState, field: str, value: str) -> None:
    _update(client, state, {field: value})


@when(parsers.parse('I clear its "{field}"'))
def when_clear(client: TestClient, state: ScenarioState, field: str) -> None:
    _update(client, state, {field: None})


@when(parsers.parse('I change the "{field}" of a nonexistent company to "{value}"'))
def when_change_nonexistent(
    client: TestClient, state: ScenarioState, field: str, value: str
) -> None:
    state.response = client.patch(f"/api/v1/companies/{uuid7()}", json={field: value})


@when("I delete that company")
def when_delete(client: TestClient, state: ScenarioState) -> None:
    state.response = client.delete(f"/api/v1/companies/{state.company_id}")


@when("I delete a nonexistent company")
def when_delete_nonexistent(client: TestClient, state: ScenarioState) -> None:
    state.response = client.delete(f"/api/v1/companies/{uuid7()}")


@when("I view that company")
def when_view(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(f"/api/v1/companies/{state.company_id}")


@when("I view a nonexistent company")
def when_view_nonexistent(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(f"/api/v1/companies/{uuid7()}")


@when("I list the companies")
def when_list(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get("/api/v1/companies")


@when(parsers.parse("I list the companies with limit {limit:d} and offset {offset:d}"))
def when_list_page(client: TestClient, state: ScenarioState, limit: int, offset: int) -> None:
    state.response = client.get("/api/v1/companies", params={"limit": limit, "offset": offset})


# --- Then ---


@then(parsers.re(f"the company {_NAME} exists with website {_WEBSITE}$"))
def then_exists_with_website(
    client: TestClient, state: ScenarioState, name: str, website: str
) -> None:
    company = _read_company(client, state)
    assert (company["name"], company["website"]) == (name, website)


@then(parsers.re(f"the company {_NAME} exists without a website$"))
def then_exists_without_website(client: TestClient, state: ScenarioState, name: str) -> None:
    company = _read_company(client, state)
    assert (company["name"], company["website"]) == (name, None)


@then(parsers.re(f"the company has {_FIELD} {_VALUE}$"))
def then_company_has(client: TestClient, state: ScenarioState, field: str, value: str) -> None:
    assert _read_company(client, state)[field] == value


@then("the company no longer exists")
def then_no_longer_exists(client: TestClient, state: ScenarioState) -> None:
    assert state.last_response.status_code == 204, state.last_response.text
    assert client.get(f"/api/v1/companies/{state.company_id}").status_code == 404


@then(parsers.re(f"I see the company {_NAME} with website {_WEBSITE}$"))
def then_see_company(state: ScenarioState, name: str, website: str) -> None:
    response = state.last_response
    assert response.status_code == 200, response.text
    assert (response.json()["name"], response.json()["website"]) == (name, website)


@then("it is rejected as invalid")
def then_invalid(state: ScenarioState) -> None:
    _assert_problem(state, 422, "validation-error")


@then("it is rejected because the company already exists")
def then_already_exists(state: ScenarioState) -> None:
    _assert_problem(state, 409, "already-exists")


@then("it is rejected because the company has applications")
def then_in_use(state: ScenarioState) -> None:
    _assert_problem(state, 409, "in-use")


@then("it is rejected because the company does not exist")
def then_not_found(state: ScenarioState) -> None:
    _assert_problem(state, 404, "not-found")


@then(parsers.parse("the companies are, in order: {names}"))
def then_companies_in_order(state: ScenarioState, names: str) -> None:
    items = state.last_response.json()["items"]
    assert [company["name"] for company in items] == _quoted(names)


@then("there are no companies")
def then_no_companies(state: ScenarioState) -> None:
    assert state.last_response.json()["items"] == []


@then(parsers.parse("there are {total:d} companies in total"))
def then_total(state: ScenarioState, total: int) -> None:
    assert state.last_response.json()["total"] == total
