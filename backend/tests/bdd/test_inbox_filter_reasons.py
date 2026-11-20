import re
from collections.abc import AsyncIterator, Iterator, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from itertools import count
from typing import Any, cast

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when
from support.clock import ZONE, FixedClock

from funnel.core.clock import get_clock
from funnel.modules.discovery.domain import WorkMode
from funnel.modules.inbox.domain import OfferReaderError, OfferText, Reading
from funnel.modules.inbox.router import get_feed_client, get_offer_reader

pytestmark = pytest.mark.bdd

scenarios("inbox/filter_reasons.feature")

OFFERS_URL = "/api/v1/offers"
PROFILES_URL = "/api/v1/search-profiles"
LIST_FIELDS = frozenset({"titles", "keywords", "excluded_keywords", "work_modes"})
YES_NO = {"yes": True, "no": False, "": None}

Row = dict[str, str]


@dataclass
class ScenarioState:
    profiles: dict[str, str] = field(default_factory=dict)
    remoteok: list[Row] = field(default_factory=list)
    remoteok_id: str | None = None
    # What the fake offer reader answers, by offer title.
    answers: dict[str, Reading] = field(default_factory=dict)
    offer: dict[str, Any] | None = None
    response: httpx2.Response | None = None
    urls: count[int] = field(default_factory=count)

    @property
    def last_response(self) -> httpx2.Response:
        assert self.response is not None, "no request was made in this scenario"
        return self.response

    @property
    def reason(self) -> dict[str, Any]:
        assert self.offer is not None, "no offer was viewed in this scenario"
        reason: dict[str, Any] | None = self.offer["filter_reason"]
        assert reason is not None, "the offer has no filter reason"
        return reason


@pytest.fixture
def state() -> ScenarioState:
    return ScenarioState()


class FakeOfferReader:
    """Answers what the scenario says; a description it knows nothing about says nothing."""

    def __init__(self, state: ScenarioState) -> None:
        self._state = state

    batch_size = 5

    async def read(self, offer: OfferText, _location: str | None) -> Reading:
        return self._state.answers.get(offer.title, Reading())

    async def read_batch(
        self, questions: Sequence[tuple[OfferText, str | None]]
    ) -> list[Reading | OfferReaderError]:
        return [await self.read(offer, location) for offer, location in questions]


@pytest.fixture(autouse=True)
def fake_sources(client: TestClient, state: ScenarioState) -> Iterator[None]:
    """Remote OK and the offer reader answer from the scenario: tests never reach the
    internet."""

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
    overrides[get_offer_reader] = lambda: FakeOfferReader(state)
    yield
    overrides.pop(get_feed_client, None)
    overrides.pop(get_offer_reader, None)


def _rows(datatable: list[list[str]]) -> list[Row]:
    header, *rows = datatable
    return [dict(zip(header, values, strict=True)) for values in rows]


def _words(text: str) -> list[str]:
    return re.split(r"\s*,\s*", text) if text else []


def _quoted(text: str) -> list[str]:
    return re.findall(r'"([^"]*)"', text)


def _offers(client: TestClient) -> list[dict[str, Any]]:
    response = client.get(OFFERS_URL, params={"limit": "100"})
    assert response.status_code == 200, response.text
    items: list[dict[str, Any]] = response.json()["items"]
    return items


def _offer_id(client: TestClient, title: str) -> str:
    offer_id: str = next(o["id"] for o in _offers(client) if o["title"] == title)
    return offer_id


def _ok(response: httpx2.Response, status: int = 201) -> dict[str, Any]:
    assert response.status_code == status, response.text
    body: dict[str, Any] = response.json() if response.content else {}
    return body


def _reading(row: Row) -> Reading:
    answers: dict[str, Any] = {
        column: YES_NO[value] if column in {"admits_location", "stable"} else value or None
        for column, value in row.items()
    }
    work_mode = answers.pop("work_mode", None)
    return Reading(work_mode=None if work_mode is None else WorkMode(work_mode), **answers)


def _expected_value(rule: str, text: str) -> str | bool | None:
    """A table cell as the API shows a rule's value: yes/no for location and stable."""
    if rule in {"location", "stable"}:
        return YES_NO[text]
    return text or None


def _rule_as_listed(rule: dict[str, Any], row: Row) -> Row:
    """The rule in the same shape as the row, only with the columns the row gives."""
    shown: dict[str, Any] = {
        "rule": rule["rule"],
        "result": rule["result"],
        "found": rule["found"],
        "missing": rule["missing"],
        "value": rule["value"],
        "evidence": rule["evidence"],
    }
    return {column: shown[column] for column in row}


def _row_as_expected(row: Row) -> dict[str, Any]:
    expected: dict[str, Any] = dict(row)
    for column in ("found", "missing"):
        if column in row:
            expected[column] = _words(row[column])
    if "value" in row:
        expected["value"] = _expected_value(row["rule"], row["value"])
    if "evidence" in row:
        expected["evidence"] = row["evidence"] or None
    return expected


# --- Given ---


@given(parsers.parse("the time is {moment}"))
def given_time(client: TestClient, moment: str) -> None:
    clock = FixedClock(datetime.fromisoformat(moment).replace(tzinfo=ZONE))
    cast(FastAPI, client.app).dependency_overrides[get_clock] = lambda: clock


@given(parsers.parse('a search profile named "{name}" with:'))
def given_profile(
    client: TestClient, state: ScenarioState, name: str, datatable: list[list[str]]
) -> None:
    body: dict[str, Any] = {"name": name}
    for key, value in datatable:
        body[key] = _words(value) if key in LIST_FIELDS else value
    state.profiles[name] = _ok(client.post(PROFILES_URL, json=body))["id"]


@given("there are no search profiles")
def given_no_profiles(client: TestClient, state: ScenarioState) -> None:
    for profile_id in state.profiles.values():
        _ok(client.delete(f"{PROFILES_URL}/{profile_id}"), 204)
    state.profiles.clear()


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


@given(parsers.parse('the job board "Remote OK" was imported with:'))
def given_job_board_imported(
    client: TestClient, state: ScenarioState, datatable: list[list[str]]
) -> None:
    state.remoteok = _rows(datatable)
    _ok(client.post(f"/api/v1/job-boards/{state.remoteok_id}/imports"))


@given(parsers.parse('the offer reader answers for "{title}":'))
def given_reader_answers(state: ScenarioState, title: str, datatable: list[list[str]]) -> None:
    state.answers[title] = _reading(_rows(datatable)[0])


@given("I read the offers")
def given_read(client: TestClient) -> None:
    _ok(client.post(f"{OFFERS_URL}/readings"))


@given(parsers.parse('an offer for "{company}" as "{title}"'))
def given_offer(client: TestClient, state: ScenarioState, company: str, title: str) -> None:
    body = {"url": f"https://jobs.example/{next(state.urls)}", "company": company, "title": title}
    _ok(client.post(OFFERS_URL, json=body))


@given(parsers.parse('I edit the profile "{name}" to have the keywords "{keywords}"'))
def given_profile_keywords(
    client: TestClient, state: ScenarioState, name: str, keywords: str
) -> None:
    body = {"keywords": _words(keywords)}
    _ok(client.patch(f"{PROFILES_URL}/{state.profiles[name]}", json=body), 200)


@given(parsers.parse('I delete the profile "{name}"'))
def given_profile_deleted(client: TestClient, state: ScenarioState, name: str) -> None:
    _ok(client.delete(f"{PROFILES_URL}/{state.profiles.pop(name)}"), 204)


@given(parsers.parse('I discarded the offer "{title}"'))
def given_discarded(client: TestClient, title: str) -> None:
    _ok(client.post(f"{OFFERS_URL}/{_offer_id(client, title)}/discard", json={}))


# --- When ---


@when(parsers.parse('I view the offer "{title}"'))
def when_view(client: TestClient, state: ScenarioState, title: str) -> None:
    state.offer = _ok(client.get(f"{OFFERS_URL}/{_offer_id(client, title)}"), 200)


@when("I list the pending offers that are near misses")
def when_list_near_misses(client: TestClient, state: ScenarioState) -> None:
    params = {"status": "pending", "near_miss": "true"}
    state.response = client.get(OFFERS_URL, params=params)


@when(parsers.parse('I list the pending offers that are failing the rule "{rule}"'))
def when_list_failing(client: TestClient, state: ScenarioState, rule: str) -> None:
    params = {"status": "pending", "failed_rule": rule}
    state.response = client.get(OFFERS_URL, params=params)


@when(parsers.parse("I list the near misses by failed rule, at most {shown:d} per rule"))
def when_list_groups(client: TestClient, state: ScenarioState, shown: int) -> None:
    state.response = client.get(f"{OFFERS_URL}/near-misses", params={"limit": shown})


@when("I count the filtered offers by failed rule")
def when_count(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(f"{OFFERS_URL}/filtered-counts")


# --- Then ---


@then(parsers.parse('the filter reason is against the profile "{name}" with:'))
def then_reason_with(state: ScenarioState, name: str, datatable: list[list[str]]) -> None:
    rows = _rows(datatable)
    rules = state.reason["rules"]
    assert state.reason["search_profile_name"] == name
    assert [rule["rule"] for rule in rules] == [row["rule"] for row in rows]
    assert [_rule_as_listed(r, row) for r, row in zip(rules, rows, strict=True)] == [
        _row_as_expected(row) for row in rows
    ]


@then(parsers.parse('the filter reason is against the profile "{name}"'))
def then_reason_profile(state: ScenarioState, name: str) -> None:
    assert state.reason["search_profile_name"] == name


@then(parsers.re(r"the filter reason says the offer has (?P<which>a|no) description$"))
def then_has_description(state: ScenarioState, which: str) -> None:
    assert state.reason["has_description"] is (which == "a")


@then(parsers.re(r"the offer is (?P<which>filtered|not filtered)$"))
def then_filtered(state: ScenarioState, which: str) -> None:
    assert state.offer is not None
    assert state.offer["filtered"] is (which == "filtered")


@then(parsers.re(r"the offer is (?P<which>a near miss|not a near miss)$"))
def then_near_miss(state: ScenarioState, which: str) -> None:
    assert state.reason["near_miss"] is (which == "a near miss")


@then(parsers.parse("the filter reason has {failed:d} failed rules"))
def then_failed_rules(state: ScenarioState, failed: int) -> None:
    results = [rule["result"] for rule in state.reason["rules"]]
    assert results.count("failed") == failed


@then("the filter reason has no reference profile and fails on the title")
def then_no_reference(state: ScenarioState) -> None:
    assert state.reason["search_profile_id"] is None
    assert [(r["rule"], r["result"]) for r in state.reason["rules"]] == [("title", "failed")]


@then("the offer has no filter reason")
def then_no_reason(state: ScenarioState) -> None:
    assert state.offer is not None
    assert state.offer["filter_reason"] is None


@then(parsers.parse("the offers are, in order, from: {companies}"))
def then_offers_from(state: ScenarioState, companies: str) -> None:
    body = _ok(state.last_response, 200)
    assert [item["company"] for item in body["items"]] == _quoted(companies)


@then(
    parsers.parse(
        "the counts are {filtered:d} filtered, of them {near_misses:d} near misses, failing:"
    )
)
def then_counts(
    state: ScenarioState, filtered: int, near_misses: int, datatable: list[list[str]]
) -> None:
    body = _ok(state.last_response, 200)
    failing = {row["rule"]: int(row["offers"]) for row in _rows(datatable)}
    counted = {key: body[key] for key in ("filtered", "near_misses", "failing")}
    assert counted == {"filtered": filtered, "near_misses": near_misses, "failing": failing}


@then("the near miss groups are:")
def then_groups(state: ScenarioState, datatable: list[list[str]]) -> None:
    body = _ok(state.last_response, 200)
    groups = [
        (group["rule"], group["total"], [offer["company"] for offer in group["offers"]])
        for group in body["groups"]
    ]
    assert groups == [
        (row["rule"], int(row["offers"]), _quoted(row["from"])) for row in _rows(datatable)
    ]


@then("there are no near miss groups")
def then_no_groups(state: ScenarioState) -> None:
    assert _ok(state.last_response, 200) == {"groups": []}


@then("it is rejected as invalid")
def then_invalid(state: ScenarioState) -> None:
    body = _ok(state.last_response, 422)
    assert body["type"].endswith("/validation-error")
