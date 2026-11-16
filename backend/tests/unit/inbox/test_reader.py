import asyncio
import json
from collections.abc import Callable
from typing import Any

import httpx2
import pytest

from funnel.modules.discovery.domain import WorkMode
from funnel.modules.inbox.domain import OfferReaderError, OfferText, Reading
from funnel.modules.inbox.reader import API, OfferReader

pytestmark = pytest.mark.unit

OFFER = OfferText("Backend Engineer", "Acme", "Fully remote. Hiring across Europe.")
ANSWER = {
    "work_mode": "remote",
    "work_mode_evidence": "Fully remote",
    "admits_location": True,
    "admits_location_evidence": "Hiring across Europe",
    "stable": None,
    "stable_evidence": None,
}

Handler = Callable[[httpx2.Request], httpx2.Response]


def _completion(content: str) -> httpx2.Response:
    return httpx2.Response(200, json={"choices": [{"message": {"content": content}}]})


def _read(handler: Handler, location: str | None = "Spain", offer: OfferText = OFFER) -> Reading:
    async def read() -> Reading:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(handler)) as client:
            return await OfferReader(client, "secret-key", "some-model").read(offer, location)

    return asyncio.run(read())


def _sent(location: str | None, offer: OfferText = OFFER) -> tuple[httpx2.Request, dict[str, Any]]:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return _completion(json.dumps(ANSWER))

    _read(handler, location, offer)
    (request,) = requests
    return request, json.loads(request.content)


def test_reads_what_the_model_answers() -> None:
    # Act
    reading = _read(lambda _request: _completion(json.dumps(ANSWER)))

    # Assert
    assert reading == Reading(
        work_mode=WorkMode.REMOTE,
        work_mode_evidence="Fully remote",
        admits_location=True,
        admits_location_evidence="Hiring across Europe",
    )


def test_asks_the_model_with_the_key_and_a_strict_schema() -> None:
    # Act
    request, body = _sent("Spain")

    # Assert
    assert str(request.url) == API
    assert request.headers["Authorization"] == "Bearer secret-key"
    assert body["model"] == "some-model"
    schema = body["response_format"]["json_schema"]
    assert schema["strict"] is True
    assert set(schema["schema"]["required"]) == set(ANSWER)
    question = body["messages"][-1]["content"]
    assert "Spain" in question
    assert OFFER.description in question


@pytest.mark.parametrize(
    ("published", "expected"),
    [
        pytest.param("USA only", "Location: USA only", id="published"),
        pytest.param(None, "Company: Acme\nDescription:", id="none-published"),
    ],
)
def test_sends_the_location_the_source_publishes(published: str | None, expected: str) -> None:
    # Arrange
    offer = OfferText("Backend Engineer", "Acme", "Fully remote.", location=published)

    # Act
    _request, body = _sent("Spain", offer)

    # Assert
    assert expected in body["messages"][-1]["content"]


def test_does_not_ask_about_the_location_without_one() -> None:
    # Act
    _request, body = _sent(None)

    # Assert
    properties = body["response_format"]["json_schema"]["schema"]["properties"]
    assert "admits_location" not in properties
    assert "Location to answer" not in body["messages"][-1]["content"]


def test_sends_the_start_and_the_end_of_a_long_description() -> None:
    # Arrange
    offer = OfferText("Backend Engineer", "Acme", "START " + "x" * 20_000 + " END")

    # Act
    _request, body = _sent("Spain", offer)

    # Assert
    question = body["messages"][-1]["content"]
    assert "START" in question
    assert "END" in question
    assert len(question) < 6_000


@pytest.mark.parametrize(
    "handler",
    [
        pytest.param(lambda _request: httpx2.Response(429, json={}), id="quota"),
        pytest.param(lambda _request: httpx2.Response(500, text="oops"), id="server-error"),
        pytest.param(lambda _request: httpx2.Response(200, text="not json"), id="not-json"),
        pytest.param(lambda _request: httpx2.Response(200, json={"choices": []}), id="no-choice"),
        pytest.param(lambda _request: _completion("not json"), id="answer-not-json"),
        pytest.param(lambda _request: _completion("[]"), id="answer-not-an-object"),
        pytest.param(
            lambda _request: _completion(json.dumps(ANSWER | {"work_mode": "sometimes"})),
            id="unknown-work-mode",
        ),
        pytest.param(
            lambda _request: _completion(json.dumps(ANSWER | {"stable": "yes"})),
            id="answer-of-another-type",
        ),
    ],
)
def test_fails_when_the_model_does_not_answer_what_was_asked(handler: Handler) -> None:
    # Act / Assert
    with pytest.raises(OfferReaderError):
        _read(handler)


def test_fails_when_the_model_cannot_be_reached() -> None:
    # Arrange
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("no network", request=request)

    # Act / Assert
    with pytest.raises(OfferReaderError):
        _read(handler)


def test_an_offer_that_fails_leaves_the_others_of_the_batch_read() -> None:
    # Arrange
    def handler(request: httpx2.Request) -> httpx2.Response:
        if b"Globex" in request.content:
            return httpx2.Response(429)
        return _completion(json.dumps(ANSWER))

    other = OfferText("Backend Engineer", "Globex", "Fully remote.")

    async def read() -> list[Reading | OfferReaderError]:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(handler)) as client:
            reader = OfferReader(client, "secret-key", "some-model")
            return await reader.read_batch([(OFFER, "Spain"), (other, "Spain")])

    # Act
    first, second = asyncio.run(read())

    # Assert
    assert isinstance(first, Reading)
    assert isinstance(second, OfferReaderError)
