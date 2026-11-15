import re
from dataclasses import dataclass, field
from itertools import count
from typing import Any
from uuid import uuid7

import httpx2
import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.bdd

scenarios("inbox/inbox.feature")

URL = "/api/v1/offers"
JOB_BOARDS_URL = "/api/v1/job-boards"
_COMPANY = r'"(?P<company>[^"]*)"'
_TITLE = r'"(?P<title>[^"]*)"'
_ADD = f"I add an offer for {_COMPANY} as {_TITLE}"
_OFFER = f"an offer for {_COMPANY} as {_TITLE}"


@dataclass
class ScenarioState:
    job_boards: dict[str, str] = field(default_factory=dict)
    offer_id: str | None = None
    response: httpx2.Response | None = None
    urls: count[int] = field(default_factory=count)

    @property
    def last_response(self) -> httpx2.Response:
        assert self.response is not None, "no request was made in this scenario"
        return self.response

    def next_url(self) -> str:
        return f"https://jobs.example/{next(self.urls)}"


@pytest.fixture
def state() -> ScenarioState:
    return ScenarioState()


def _quoted(text: str) -> list[str]:
    return re.findall(r'"([^"]*)"', text)


def _body(state: ScenarioState, company: str, title: str) -> dict[str, Any]:
    return {"url": state.next_url(), "company": company, "title": title}


def _add(client: TestClient, state: ScenarioState, body: dict[str, Any]) -> None:
    state.response = client.post(URL, json=body)
    if state.response.status_code == 201:
        state.offer_id = state.response.json()["id"]


def _given_offer(client: TestClient, state: ScenarioState, body: dict[str, Any]) -> None:
    response = client.post(URL, json=body)
    assert response.status_code == 201, response.text
    state.offer_id = response.json()["id"]


def _act(client: TestClient, state: ScenarioState, action: str) -> httpx2.Response:
    """Discard, restore or promote the scenario's offer."""
    offer_url = f"{URL}/{state.offer_id}"
    match action:
        case "discard":
            return client.post(f"{offer_url}/discard", json={})
        case "restore":
            return client.delete(f"{offer_url}/discard")
        case "promote":
            return client.post(f"{offer_url}/promotion", json={})
    raise AssertionError(f"unknown action {action}")


def _read_offer(client: TestClient, state: ScenarioState) -> dict[str, Any]:
    response = client.get(f"{URL}/{state.offer_id}")
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _read_application(client: TestClient, state: ScenarioState) -> dict[str, Any]:
    application_id = _read_offer(client, state)["application_id"]
    assert application_id is not None, "the offer was not promoted"
    response = client.get(f"/api/v1/applications/{application_id}")
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _company_names(client: TestClient) -> list[str]:
    response = client.get("/api/v1/companies")
    assert response.status_code == 200, response.text
    return [item["name"] for item in response.json()["items"]]


def _assert_problem(state: ScenarioState, status: int, slug: str) -> None:
    response = state.last_response
    assert (response.status_code, response.json()["type"]) == (status, f"/problems/{slug}")


# --- Given ---


@given(parsers.parse('a job board named "{name}"'))
def given_job_board(client: TestClient, state: ScenarioState, name: str) -> None:
    body = {
        "name": name,
        "search_url_template": "https://jobs.example/search?q={query}",
        "syntax": "keywords",
    }
    response = client.post(JOB_BOARDS_URL, json=body)
    assert response.status_code == 201, response.text
    state.job_boards[name] = response.json()["id"]


@given(parsers.parse('a company named "{name}"'))
def given_company(client: TestClient, name: str) -> None:
    response = client.post("/api/v1/companies", json={"name": name})
    assert response.status_code == 201, response.text


@given(parsers.re(f"{_OFFER}$"))
def given_offer(client: TestClient, state: ScenarioState, company: str, title: str) -> None:
    _given_offer(client, state, _body(state, company, title))


@given(parsers.re(f'{_OFFER} with URL "(?P<url>[^"]+)"$'))
def given_offer_with_url(
    client: TestClient, state: ScenarioState, company: str, title: str, url: str
) -> None:
    _given_offer(client, state, _body(state, company, title) | {"url": url})


@given(parsers.re(f'{_OFFER} from "(?P<job_board>[^"]+)"$'))
def given_offer_from(
    client: TestClient, state: ScenarioState, company: str, title: str, job_board: str
) -> None:
    body = _body(state, company, title) | {"job_board_id": state.job_boards[job_board]}
    _given_offer(client, state, body)


@given(parsers.re(f"{_OFFER} that was (?P<status>discarded|promoted)$"))
def given_offer_in_status(
    client: TestClient, state: ScenarioState, company: str, title: str, status: str
) -> None:
    _given_offer(client, state, _body(state, company, title))
    response = _act(client, state, "discard" if status == "discarded" else "promote")
    assert response.status_code == 201, response.text


@given(parsers.parse('offers for "{company}" as {titles}, added in that order'))
def given_offers(client: TestClient, state: ScenarioState, company: str, titles: str) -> None:
    for title in _quoted(titles):
        _given_offer(client, state, _body(state, company, title))


# --- When ---


@when("I add an offer with:")
def when_add_with(client: TestClient, state: ScenarioState, datatable: list[list[str]]) -> None:
    body: dict[str, Any] = dict(datatable)
    if "job_board" in body:
        body["job_board_id"] = state.job_boards[body.pop("job_board")]
    _add(client, state, body)


@when(parsers.re(f"{_ADD}$"))
def when_add(client: TestClient, state: ScenarioState, company: str, title: str) -> None:
    _add(client, state, _body(state, company, title))


@when(parsers.re(f'{_ADD} with "(?P<field>[^"]*)" set to "(?P<value>[^"]*)"$'))
def when_add_with_field(
    client: TestClient, state: ScenarioState, company: str, title: str, field: str, value: str
) -> None:
    _add(client, state, _body(state, company, title) | {field: value})


@when(parsers.re(f'{_ADD} with URL "(?P<url>[^"]+)"$'))
def when_add_with_url(
    client: TestClient, state: ScenarioState, company: str, title: str, url: str
) -> None:
    _add(client, state, _body(state, company, title) | {"url": url})


@when(parsers.re(f"{_ADD} from a nonexistent job board$"))
def when_add_from_nonexistent_board(
    client: TestClient, state: ScenarioState, company: str, title: str
) -> None:
    _add(client, state, _body(state, company, title) | {"job_board_id": str(uuid7())})


@when("I view a nonexistent offer")
def when_view_nonexistent(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(f"{URL}/{uuid7()}")


@when("I list the offers")
def when_list(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(URL)


@when(parsers.parse('I list the offers with status "{status}"'))
def when_list_with_status(client: TestClient, state: ScenarioState, status: str) -> None:
    state.response = client.get(URL, params={"status": status})


def _discard(client: TestClient, state: ScenarioState, body: dict[str, str]) -> httpx2.Response:
    return client.post(f"{URL}/{state.offer_id}/discard", json=body)


@when(parsers.re(r'I discard it because "(?P<reason>[^"]*)"$'))
def when_discard_because(client: TestClient, state: ScenarioState, reason: str) -> None:
    state.response = _discard(client, state, {"reason": reason})


@when(parsers.re(r'I discard it because "(?P<reason>[^"]*)" with the word "(?P<word>[^"]*)"$'))
def when_discard_with_word(
    client: TestClient, state: ScenarioState, reason: str, word: str
) -> None:
    body = {"reason": reason} | ({"word": word} if word else {})
    state.response = _discard(client, state, body)


@when(parsers.parse('I discard it because of the word "{word}"'))
def when_discard_word(client: TestClient, state: ScenarioState, word: str) -> None:
    state.response = _discard(client, state, {"reason": "title_word", "word": word})


@given(parsers.parse('I discarded it because of the word "{word}"'))
def given_discarded_word(client: TestClient, state: ScenarioState, word: str) -> None:
    response = _discard(client, state, {"reason": "title_word", "word": word})
    assert response.status_code == 201, response.text


@when(parsers.re(r"I (?P<action>discard|restore|promote) it$"))
def when_act(client: TestClient, state: ScenarioState, action: str) -> None:
    state.response = _act(client, state, action)


@when(parsers.parse('I promote it through "{channel}"'))
def when_promote_through(client: TestClient, state: ScenarioState, channel: str) -> None:
    url = f"{URL}/{state.offer_id}/promotion"
    state.response = client.post(url, json={"channel": channel})


@when("I promote a nonexistent offer")
def when_promote_nonexistent(client: TestClient, state: ScenarioState) -> None:
    state.response = client.post(f"{URL}/{uuid7()}/promotion", json={})


@when(parsers.parse('I delete the job board "{name}"'))
def when_delete_job_board(client: TestClient, state: ScenarioState, name: str) -> None:
    state.response = client.delete(f"{JOB_BOARDS_URL}/{state.job_boards[name]}")


# --- Then ---


@then("the offer has:")
def then_offer_has(client: TestClient, state: ScenarioState, datatable: list[list[str]]) -> None:
    offer = _read_offer(client, state)
    renamed = {"job_board": "job_board_name"}
    actual = {name: offer[renamed.get(name, name)] for name, _ in datatable}
    assert actual == dict(datatable)


@then(parsers.parse('the offer is "{status}"'))
def then_offer_is(client: TestClient, state: ScenarioState, status: str) -> None:
    assert _read_offer(client, state)["status"] == status


@then("the offer has no job board")
def then_no_job_board(client: TestClient, state: ScenarioState) -> None:
    offer = _read_offer(client, state)
    assert (offer["job_board_id"], offer["job_board_name"]) == (None, None)


def _discard_of(client: TestClient, state: ScenarioState) -> tuple[str, str | None, str | None]:
    offer = _read_offer(client, state)
    return offer["status"], offer["discard_reason"], offer["discard_word"]


@then(parsers.parse('the offer is "{status}" with reason "{reason}" and no word'))
def then_offer_with_reason(
    client: TestClient, state: ScenarioState, status: str, reason: str
) -> None:
    assert _discard_of(client, state) == (status, reason, None)


@then(parsers.parse('the offer is "{status}" with reason "{reason}" and word "{word}"'))
def then_offer_with_word(
    client: TestClient, state: ScenarioState, status: str, reason: str, word: str
) -> None:
    assert _discard_of(client, state) == (status, reason, word)


@then(parsers.parse('the offer is "{status}" with no reason and no word'))
def then_offer_without_reason(client: TestClient, state: ScenarioState, status: str) -> None:
    assert _discard_of(client, state) == (status, None, None)


@then("it is rejected because the word is not in the title")
def then_word_not_in_title(state: ScenarioState) -> None:
    _assert_problem(state, 422, "word-not-in-title")


@then("it is rejected as invalid")
def then_invalid(state: ScenarioState) -> None:
    _assert_problem(state, 422, "validation-error")


@then("it is rejected because the job board does not exist")
def then_unknown_job_board(state: ScenarioState) -> None:
    _assert_problem(state, 422, "unknown-job-board")


@then("it is rejected because the offer already exists")
def then_already_exists(state: ScenarioState) -> None:
    _assert_problem(state, 409, "already-exists")


@then("it is rejected because the offer does not exist")
def then_not_found(state: ScenarioState) -> None:
    _assert_problem(state, 404, "not-found")


@then("it is rejected because the offer is not in a valid status")
def then_invalid_status(state: ScenarioState) -> None:
    _assert_problem(state, 409, "invalid-offer-status")


@then("it is rejected because the job board has offers")
def then_job_board_in_use(state: ScenarioState) -> None:
    _assert_problem(state, 409, "in-use")


@then(parsers.parse("the offers are, in order: {titles}"))
def then_offers_in_order(state: ScenarioState, titles: str) -> None:
    response = state.last_response
    assert response.status_code == 200, response.text
    assert [item["title"] for item in response.json()["items"]] == _quoted(titles)


@then(parsers.parse("there are {total:d} offers in total"))
def then_total(state: ScenarioState, total: int) -> None:
    assert state.last_response.json()["total"] == total


@then(
    parsers.parse(
        'its application is in stage "{stage}" for "{company}" as "{role}" '
        'through "{channel}" with URL "{url}"'
    )
)
def then_application(
    client: TestClient,
    state: ScenarioState,
    stage: str,
    company: str,
    role: str,
    channel: str,
    url: str,
) -> None:
    application = _read_application(client, state)
    fields = ("stage", "company_name", "role", "channel", "url")
    assert tuple(application[name] for name in fields) == (stage, company, role, channel, url)


@then(parsers.parse("its application's history starts on {day}"))
def then_history_starts(client: TestClient, state: ScenarioState, day: str) -> None:
    assert _read_application(client, state)["transitions"][0]["occurred_on"] == day


@then(parsers.parse('its application is through "{channel}"'))
def then_application_channel(client: TestClient, state: ScenarioState, channel: str) -> None:
    assert _read_application(client, state)["channel"] == channel


@then(parsers.parse('its application is for the company "{name}"'))
def then_application_company(client: TestClient, state: ScenarioState, name: str) -> None:
    assert _read_application(client, state)["company_name"] == name


@then(parsers.parse("there is {total:d} company in total"))
def then_company_total(client: TestClient, total: int) -> None:
    assert len(_company_names(client)) == total


@then(parsers.parse('there is a company named "{name}"'))
def then_company_exists(client: TestClient, name: str) -> None:
    assert name in _company_names(client)
