import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx2
import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when
from support.factories import ApplicationDetails, make_application

from funnel.core.config import Settings
from funnel.modules.applications.domain import Channel, Outcome, Stage

pytestmark = pytest.mark.bdd

scenarios("metrics/funnel_metrics.feature")


@dataclass
class ScenarioState:
    company_id: UUID | None = None
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


def _rows(datatable: list[list[str]]) -> list[dict[str, str]]:
    header, *rows = datatable
    return [dict(zip(header, values, strict=True)) for values in rows]


def _expected_steps(datatable: list[list[str]]) -> list[dict[str, Any]]:
    return [
        {
            "from_stage": row["from"],
            "to_stage": row["to"],
            "reached_from": int(row["reached_from"]),
            "reached_to": int(row["reached_to"]),
            "rate": float(row["rate"]) if row["rate"] else None,
        }
        for row in _rows(datatable)
    ]


# --- Given ---


@given(parsers.parse('a company named "{name}"'))
def given_company(client: TestClient, state: ScenarioState, name: str) -> None:
    response = client.post("/api/v1/companies", json={"name": name})
    assert response.status_code == 201, response.text
    state.company_id = UUID(response.json()["id"])


@given("these applications:")
def given_applications(
    settings: Settings, state: ScenarioState, datatable: list[list[str]]
) -> None:
    for row in _rows(datatable):
        details = ApplicationDetails(company_id=state.company_id, channel=Channel(row["channel"]))
        make_application(
            settings.database_url,
            stage=Stage(row["stage"]),
            outcome=Outcome(row["outcome"]) if row["outcome"] else None,
            details=details,
        )


# --- When ---


@when("I view the conversion by stage")
def when_view_conversion(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get("/api/v1/metrics/conversion")


@when("I view the conversion by channel")
def when_view_conversion_by_channel(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get("/api/v1/metrics/conversion-by-channel")


@when("I view the active pipeline")
def when_view_pipeline(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get("/api/v1/metrics/pipeline")


# --- Then ---


@then("the conversion is:")
def then_conversion_is(state: ScenarioState, datatable: list[list[str]]) -> None:
    assert state.body["steps"] == _expected_steps(datatable)


@then(parsers.parse("the channels are, in order: {channels}"))
def then_channels_in_order(state: ScenarioState, channels: str) -> None:
    listed = [item["channel"] for item in state.body["channels"]]
    assert listed == re.findall(r'"([^"]*)"', channels)


@then(parsers.parse('the conversion for channel "{channel}" is:'))
def then_channel_conversion_is(
    state: ScenarioState, channel: str, datatable: list[list[str]]
) -> None:
    steps = {item["channel"]: item["steps"] for item in state.body["channels"]}
    assert steps[channel] == _expected_steps(datatable)


@then("there are no channels")
def then_no_channels(state: ScenarioState) -> None:
    assert state.body["channels"] == []


@then("the active pipeline is:")
def then_pipeline_is(state: ScenarioState, datatable: list[list[str]]) -> None:
    expected = [
        {"stage": row["stage"], "applications": int(row["applications"])}
        for row in _rows(datatable)
    ]
    assert state.body["stages"] == expected


@then(parsers.parse("there are {total:d} active applications in total"))
def then_pipeline_total(state: ScenarioState, total: int) -> None:
    assert state.body["total"] == total
