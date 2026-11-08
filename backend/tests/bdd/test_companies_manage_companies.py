import re
from dataclasses import dataclass
from typing import Any
from uuid import uuid7

import httpx2
import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.bdd

scenarios("companies/manage_companies.feature")

# `[^"]*` instead of parse's `{}`: an empty name must still match the step.
_NAME = r'"(?P<name>[^"]*)"'
_WEBSITE = r'"(?P<website>[^"]*)"'


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


def _read_created(client: TestClient, state: ScenarioState) -> dict[str, Any]:
    created = state.last_response
    assert created.status_code == 201, created.text
    response = client.get(f"/api/v1/companies/{created.json()['id']}")
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _assert_problem(state: ScenarioState, status: int, slug: str) -> None:
    response = state.last_response
    assert (response.status_code, response.json()["type"]) == (status, f"/problems/{slug}")


# --- Given ---


@given(parsers.re(f"a company named {_NAME}$"))
def given_company(client: TestClient, state: ScenarioState, name: str) -> None:
    response = _create(client, {"name": name})
    assert response.status_code == 201, response.text
    state.company_id = response.json()["id"]


@given(parsers.re(f"a company named {_NAME} with website {_WEBSITE}$"))
def given_company_with_website(
    client: TestClient, state: ScenarioState, name: str, website: str
) -> None:
    response = _create(client, {"name": name, "website": website})
    assert response.status_code == 201, response.text
    state.company_id = response.json()["id"]


@given(parsers.parse("companies named {names}"))
def given_companies(client: TestClient, names: str) -> None:
    for name in _quoted(names):
        response = _create(client, {"name": name})
        assert response.status_code == 201, response.text


# --- When ---


@when(parsers.re(f"I create a company named {_NAME}$"))
def when_create(client: TestClient, state: ScenarioState, name: str) -> None:
    state.response = _create(client, {"name": name})


@when(parsers.re(f"I create a company named {_NAME} with website {_WEBSITE}$"))
def when_create_with_website(
    client: TestClient, state: ScenarioState, name: str, website: str
) -> None:
    state.response = _create(client, {"name": name, "website": website})


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
    company = _read_created(client, state)
    assert (company["name"], company["website"]) == (name, website)


@then(parsers.re(f"the company {_NAME} exists without a website$"))
def then_exists_without_website(client: TestClient, state: ScenarioState, name: str) -> None:
    company = _read_created(client, state)
    assert (company["name"], company["website"]) == (name, None)


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
