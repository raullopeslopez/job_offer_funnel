from dataclasses import dataclass, field
from itertools import count
from typing import Any
from uuid import uuid7

import httpx2
import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.bdd

scenarios("inbox/offer_search.feature")

URL = "/api/v1/offers"
_OFFER = r'an offer for "(?P<company>[^"]*)" as "(?P<title>[^"]*)"'
_LIST = "I list the offers"


@dataclass
class ScenarioState:
    job_boards: dict[str, str] = field(default_factory=dict)
    response: httpx2.Response | None = None
    urls: count[int] = field(default_factory=count)

    @property
    def last_response(self) -> httpx2.Response:
        assert self.response is not None, "no request was made in this scenario"
        return self.response


@pytest.fixture
def state() -> ScenarioState:
    return ScenarioState()


def _add_offer(
    client: TestClient, state: ScenarioState, company: str, title: str, **extra: Any
) -> str:
    body = {"url": f"https://jobs.example/{next(state.urls)}", "company": company, "title": title}
    response = client.post(URL, json=body | extra)
    assert response.status_code == 201, response.text
    offer_id: str = response.json()["id"]
    return offer_id


def _list(client: TestClient, state: ScenarioState, **params: str) -> None:
    state.response = client.get(URL, params=params)


# --- Given ---


@given(parsers.parse('a job board named "{name}"'))
def given_job_board(client: TestClient, state: ScenarioState, name: str) -> None:
    body = {
        "name": name,
        "search_url_template": "https://jobs.example/search?q={query}",
        "syntax": "keywords",
    }
    response = client.post("/api/v1/job-boards", json=body)
    assert response.status_code == 201, response.text
    state.job_boards[name] = response.json()["id"]


@given(parsers.re(f"{_OFFER}$"))
def given_offer(client: TestClient, state: ScenarioState, company: str, title: str) -> None:
    _add_offer(client, state, company, title)


@given(parsers.re(f'{_OFFER} from "(?P<job_board>[^"]+)"$'))
def given_offer_from(
    client: TestClient, state: ScenarioState, company: str, title: str, job_board: str
) -> None:
    _add_offer(client, state, company, title, job_board_id=state.job_boards[job_board])


@given(parsers.re(f"{_OFFER} that was discarded$"))
def given_discarded_offer(
    client: TestClient, state: ScenarioState, company: str, title: str
) -> None:
    offer_id = _add_offer(client, state, company, title)
    response = client.post(f"{URL}/{offer_id}/discard", json={})
    assert response.status_code == 201, response.text


# --- When ---


@when(parsers.re(f'{_LIST} searching for "(?P<text>[^"]*)"$'))
def when_search(client: TestClient, state: ScenarioState, text: str) -> None:
    _list(client, state, matching_company_or_title=text)


@when(parsers.re(f'{_LIST} from "(?P<job_board>[^"]+)"$'))
def when_list_from(client: TestClient, state: ScenarioState, job_board: str) -> None:
    _list(client, state, job_board_id=state.job_boards[job_board])


@when(f"{_LIST} from a nonexistent job board")
def when_list_from_nonexistent(client: TestClient, state: ScenarioState) -> None:
    _list(client, state, job_board_id=str(uuid7()))


@when(parsers.re(f'{_LIST} from "(?P<job_board>[^"]+)" searching for "(?P<text>[^"]*)"$'))
def when_search_from(client: TestClient, state: ScenarioState, job_board: str, text: str) -> None:
    _list(client, state, job_board_id=state.job_boards[job_board], matching_company_or_title=text)


@when(parsers.re(f'{_LIST} with status "(?P<status>[^"]+)" searching for "(?P<text>[^"]*)"$'))
def when_search_with_status(
    client: TestClient, state: ScenarioState, status: str, text: str
) -> None:
    _list(client, state, status=status, matching_company_or_title=text)


# --- Then ---


@then(parsers.re(r'the offers are, in order: "(?P<titles>[^"]*)"$'))
def then_offers_in_order(state: ScenarioState, titles: str) -> None:
    response = state.last_response
    assert response.status_code == 200, response.text
    expected = [title.strip() for title in titles.split(",")] if titles else []
    assert [item["title"] for item in response.json()["items"]] == expected


@then(parsers.re(r"there (?:is|are) (?P<total>\d+) offers? in total$"))
def then_total(state: ScenarioState, total: str) -> None:
    response = state.last_response
    assert response.status_code == 200, response.text
    assert response.json()["total"] == int(total)
