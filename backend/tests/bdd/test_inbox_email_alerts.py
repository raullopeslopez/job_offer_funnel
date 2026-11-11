import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, cast

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when
from support.clock import ZONE, FixedClock

from funnel.core.clock import get_clock

pytestmark = pytest.mark.bdd

scenarios("inbox/email_alerts.feature")

OFFERS_URL = "/api/v1/offers"
JOB_BOARDS_URL = "/api/v1/job-boards"
IMPORTS_URL = "/api/v1/email-alerts/imports"
LINKEDIN_SENDER = "jobalerts-noreply@linkedin.com"
TRACKING = "?trackingId=abc%3D%3D&refId=def&trk=eml-email_job_alert_digest_01&otpToken=xyz"
SEPARATOR = "\n\n---------------------------------------------------------\n\n"

Row = dict[str, str]


def _linkedin_alert(rows: list[Row]) -> str:
    """A LinkedIn job alert's plain-text body, shaped like the real ones (2026-11-11)."""
    jobs = [
        f"{r['title']}\n{r['company']}\n{r['location']}\nCrecimiento rápido\n\n1 contacto\n"
        f"Ver anuncio de empleo: https://www.linkedin.com/comm/jobs/view/{r['job']}/{TRACKING}"
        for r in rows
    ]
    footer = (
        "Ver todos los empleos en LinkedIn: https://www.linkedin.com/comm/jobs/search-results/"
        "?keywords=Back+End+Developer\nGestionar tus alertas de empleo: "
        "https://www.linkedin.com/comm/jobs/alerts\n\n----------------------------------------\n\n"
        "Recibes emails sobre alertas de empleo.\n© 2026 LinkedIn Ireland Unlimited Company."
    )
    heading = "Tu alerta de empleo para Back End Developer en Unión Europea"
    return heading + "\n" + SEPARATOR.join([*jobs, footer])


@dataclass
class ScenarioState:
    now: datetime | None = None
    sender: str = LINKEDIN_SENDER
    job_boards: dict[str, str] = field(default_factory=dict)
    text: str = ""
    response: httpx2.Response | None = None

    @property
    def last_response(self) -> httpx2.Response:
        assert self.response is not None, "no request was made in this scenario"
        return self.response


@pytest.fixture
def state() -> ScenarioState:
    return ScenarioState()


def _rows(datatable: list[list[str]]) -> list[Row]:
    header, *rows = datatable
    return [dict(zip(header, values, strict=True)) for values in rows]


def _import(client: TestClient, state: ScenarioState) -> httpx2.Response:
    return client.post(IMPORTS_URL, json={"sender": state.sender, "text": state.text})


def _offer(client: TestClient, title: str) -> dict[str, Any]:
    response = client.get(OFFERS_URL)
    assert response.status_code == 200, response.text
    offers: list[dict[str, Any]] = response.json()["items"]
    return next(offer for offer in offers if offer["title"] == title)


# --- Given ---


@given(parsers.parse("the time is {moment}"))
def given_time(client: TestClient, state: ScenarioState, moment: str) -> None:
    state.now = datetime.fromisoformat(moment).replace(tzinfo=ZONE)
    clock = FixedClock(state.now)
    cast(FastAPI, client.app).dependency_overrides[get_clock] = lambda: clock


@given(parsers.parse('a search profile named "{name}" with:'))
def given_profile(client: TestClient, name: str, datatable: list[list[str]]) -> None:
    body: dict[str, Any] = {"name": name}
    for key, value in datatable:
        body[key] = re.split(r"\s*,\s*", value)
    response = client.post("/api/v1/search-profiles", json=body)
    assert response.status_code == 201, response.text


@given(parsers.parse('a job board named "{name}" imported from the email alert "{email_alert}"'))
def given_email_job_board(
    client: TestClient, state: ScenarioState, name: str, email_alert: str
) -> None:
    body = {
        "name": name,
        "search_url_template": "https://www.linkedin.com/jobs/search/?keywords={query}",
        "syntax": "boolean",
        "import_method": "email",
        "email_alert": email_alert,
    }
    response = client.post(JOB_BOARDS_URL, json=body)
    assert response.status_code == 201, response.text
    state.job_boards[name] = response.json()["id"]


@given(parsers.parse('the job board "{name}" is no longer imported'))
def given_not_imported(client: TestClient, state: ScenarioState, name: str) -> None:
    url = f"{JOB_BOARDS_URL}/{state.job_boards[name]}"
    response = client.patch(url, json={"import_method": "none"})
    assert response.status_code == 200, response.text


@given("a LinkedIn job alert with:")
def given_linkedin_alert(state: ScenarioState, datatable: list[list[str]]) -> None:
    state.text = _linkedin_alert(_rows(datatable))


@given("a LinkedIn job alert with no offers")
def given_empty_linkedin_alert(state: ScenarioState) -> None:
    state.text = _linkedin_alert([])


@given(parsers.parse('an email from "{sender}" with a LinkedIn job alert\'s content'))
def given_email_from(state: ScenarioState, sender: str) -> None:
    state.sender = sender
    rows = [{"title": "Backend Engineer", "company": "Acme", "location": "Spain", "job": "1"}]
    state.text = _linkedin_alert(rows)


@given("I imported the alert")
def given_imported(client: TestClient, state: ScenarioState) -> None:
    response = _import(client, state)
    assert response.status_code == 201, response.text


# --- When ---


@when("I import the alert")
def when_import(client: TestClient, state: ScenarioState) -> None:
    state.response = _import(client, state)


# --- Then ---


@then(
    parsers.parse(
        "the import found {found:d} offers, {added:d} added, {filtered:d} filtered"
        " and {already:d} already in the inbox"
    )
)
def then_import_counts(  # noqa: PLR0913, PLR0917  # one argument per number in the step
    state: ScenarioState, found: int, added: int, filtered: int, already: int
) -> None:
    response = state.last_response
    assert response.status_code == 201, response.text
    body = response.json()
    counts = (body["found"], body["added"], body["filtered"], body["already_in_inbox"])
    assert counts == (found, added, filtered, already)


@then(parsers.parse("the pending offers are: {titles}"))
def then_pending_offers(client: TestClient, titles: str) -> None:
    response = client.get(OFFERS_URL, params={"status": "pending"})
    assert response.status_code == 200, response.text
    expected = re.findall(r'"([^"]*)"', titles)
    assert [item["title"] for item in response.json()["items"]] == expected


@then(parsers.parse('the offer "{title}" links to "{url}" and comes from the job board "{name}"'))
def then_offer_source(
    client: TestClient, state: ScenarioState, title: str, url: str, name: str
) -> None:
    offer = _offer(client, title)
    assert (offer["url"], offer["job_board_id"]) == (url, state.job_boards[name])


REJECTIONS = {
    "the email is not a supported alert": (422, "unsupported-alert"),
    "no job board imports that email alert": (409, "email-alert-not-imported"),
}


@then(parsers.re(f"it is rejected because (?P<reason>{'|'.join(REJECTIONS)})$"))
def then_rejected(state: ScenarioState, reason: str) -> None:
    response = state.last_response
    status, slug = REJECTIONS[reason]
    assert (response.status_code, response.json()["type"]) == (status, f"/problems/{slug}")


@then("there are no offers in the inbox")
def then_no_offers(client: TestClient) -> None:
    response = client.get(OFFERS_URL)
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 0
