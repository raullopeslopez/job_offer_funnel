import re
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid7

import httpx2
import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.bdd

scenarios("discovery/generated_searches.feature")

PROFILES_URL = "/api/v1/search-profiles"
JOB_BOARDS_URL = "/api/v1/job-boards"
TEMPLATE = "https://jobs.example/search?q={query}"
LIST_FIELDS = frozenset({"titles", "keywords", "excluded_keywords", "work_modes"})


@dataclass
class ScenarioState:
    profiles: dict[str, str] = field(default_factory=dict)
    response: httpx2.Response | None = None

    @property
    def body(self) -> dict[str, Any]:
        assert self.response is not None, "no request was made in this scenario"
        assert self.response.status_code == 200, self.response.text
        body: dict[str, Any] = self.response.json()
        return body


@pytest.fixture
def state() -> ScenarioState:
    return ScenarioState()


def _quoted(text: str) -> list[str]:
    return re.findall(r'"([^"]*)"', text)


def _api_value(field_name: str, value: str) -> object:
    return re.split(r"\s*,\s*", value) if field_name in LIST_FIELDS else value


def _searches_for(state: ScenarioState, job_board: str) -> list[dict[str, str]]:
    by_name = {item["job_board_name"]: item["searches"] for item in state.body["job_boards"]}
    searches: list[dict[str, str]] = by_name[job_board]
    return searches


def _create_job_board(client: TestClient, name: str, syntax: str, template: str) -> None:
    body = {"name": name, "search_url_template": template, "syntax": syntax}
    response = client.post(JOB_BOARDS_URL, json=body)
    assert response.status_code == 201, response.text


# --- Given ---


@given(parsers.parse('a search profile named "{name}" with:'))
def given_profile(
    client: TestClient, state: ScenarioState, name: str, datatable: list[list[str]]
) -> None:
    body = {"name": name} | {key: _api_value(key, value) for key, value in datatable}
    response = client.post(PROFILES_URL, json=body)
    assert response.status_code == 201, response.text
    state.profiles[name] = response.json()["id"]


@given(parsers.re(r'a job board named "(?P<name>[^"]+)" with syntax "(?P<syntax>[^"]+)"$'))
def given_job_board(client: TestClient, name: str, syntax: str) -> None:
    _create_job_board(client, name, syntax, TEMPLATE)


@given(parsers.parse('a job board named "{name}" imported from the feed "{feed}"'))
def given_imported_job_board(client: TestClient, name: str, feed: str) -> None:
    body = {
        "name": name,
        "search_url_template": TEMPLATE,
        "syntax": "keywords",
        "import_method": "api",
        "feed": feed,
    }
    response = client.post(JOB_BOARDS_URL, json=body)
    assert response.status_code == 201, response.text


@given(parsers.parse('a job board named "{name}" with syntax "{syntax}" and template "{template}"'))
def given_job_board_with_template(
    client: TestClient, name: str, syntax: str, template: str
) -> None:
    _create_job_board(client, name, syntax, template)


# --- When ---


@when(parsers.parse('I generate the searches of the profile "{name}"'))
def when_generate(client: TestClient, state: ScenarioState, name: str) -> None:
    state.response = client.get(f"{PROFILES_URL}/{state.profiles[name]}/searches")


@when("I generate the searches of a nonexistent profile")
def when_generate_nonexistent(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(f"{PROFILES_URL}/{uuid7()}/searches")


# --- Then ---


@then(parsers.parse('the searches for "{job_board}" have the queries:'))
def then_queries(state: ScenarioState, job_board: str, datatable: list[list[str]]) -> None:
    _, *rows = datatable
    queries = [search["query"] for search in _searches_for(state, job_board)]
    assert queries == [query for (query,) in rows]


@then(parsers.parse('the searches for "{job_board}" have the URLs:'))
def then_urls(state: ScenarioState, job_board: str, datatable: list[list[str]]) -> None:
    _, *rows = datatable
    urls = [search["url"] for search in _searches_for(state, job_board)]
    assert urls == [url for (url,) in rows]


@then(parsers.parse("the job boards with searches are, in order: {names}"))
def then_job_boards_in_order(state: ScenarioState, names: str) -> None:
    listed = [item["job_board_name"] for item in state.body["job_boards"]]
    assert listed == _quoted(names)


@then(parsers.parse('the work modes to filter by are "{work_modes}"'))
def then_work_modes(state: ScenarioState, work_modes: str) -> None:
    assert state.body["work_modes"] == _api_value("work_modes", work_modes)


@then("there are no searches")
def then_no_searches(state: ScenarioState) -> None:
    assert state.body["job_boards"] == []


@then("it is rejected because the search profile does not exist")
def then_not_found(state: ScenarioState) -> None:
    response = state.response
    assert response is not None
    assert (response.status_code, response.json()["type"]) == (404, "/problems/not-found")
