import asyncio
import json
from collections.abc import Callable
from typing import Any

import httpx2
import pytest

from funnel.modules.discovery.domain import SearchTerms
from funnel.modules.inbox.domain import (
    Decision,
    DiscardReason,
    Mistake,
    OfferStatus,
    OfferText,
    OfferTriagerError,
    TriageAnswer,
    TriageContext,
    TriageMistake,
    TriageReply,
    TriagerSuggestion,
)
from funnel.modules.inbox.reader import API
from funnel.modules.inbox.triager import OfferTriager

pytestmark = pytest.mark.unit

OFFERS = [
    OfferText("Backend Engineer", "Acme", "Python services for a crypto exchange."),
    OfferText("Backend Engineer", "Globex", "Go services."),
]
CONTEXT = TriageContext(
    profiles=[SearchTerms(["Backend Engineer"], [], ["Senior"], name="Backend")],
    decisions=[
        Decision("Data Engineer", OfferStatus.DISCARDED, DiscardReason.STACK),
        Decision("Backend Engineer Lead", OfferStatus.PROMOTED),
    ],
    mistakes=[
        TriageMistake("Rust Engineer", Mistake.REJECTED_SUGGESTION, DiscardReason.STACK),
        TriageMistake("Senior Engineer", Mistake.MISSED_DISCARD),
    ],
)
ANSWER = {
    "offers": [
        {
            "offer": 0,
            "verdict": "ko",
            "why": "Crypto.",
            "reason": "company",
            "evidence": "for a crypto exchange",
        },
        {"offer": 1, "verdict": "ok", "why": "Fits.", "reason": None, "evidence": None},
    ],
    "exclusions": [{"profile": "Backend", "word": "crypto", "why": "Noise.", "offers": [0]}],
}

Handler = Callable[[httpx2.Request], httpx2.Response]


def _completion(content: str) -> httpx2.Response:
    return httpx2.Response(200, json={"choices": [{"message": {"content": content}}]})


def _triage(handler: Handler, offers: list[OfferText] = OFFERS) -> TriageReply:
    async def triage() -> TriageReply:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(handler)) as client:
            return await OfferTriager(client, "secret-key", "some-model").triage(offers, CONTEXT)

    return asyncio.run(triage())


def _sent(offers: list[OfferText] = OFFERS) -> tuple[httpx2.Request, dict[str, Any]]:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return _completion(json.dumps(ANSWER))

    _triage(handler, offers)
    (request,) = requests
    return request, json.loads(request.content)


def test_reads_what_the_model_answers_for_each_offer() -> None:
    # Act
    reply = _triage(lambda _request: _completion(json.dumps(ANSWER)))

    # Assert
    assert reply.answers == {
        0: TriageAnswer("ko", "Crypto.", "company", "for a crypto exchange"),
        1: TriageAnswer("ok", "Fits."),
    }
    assert reply.suggestions == [TriagerSuggestion("Backend", "crypto", "Noise.", [0])]


def test_asks_once_for_the_batch_with_the_context_and_a_strict_schema() -> None:
    # Act
    request, body = _sent()

    # Assert
    assert str(request.url) == API
    assert request.headers["Authorization"] == "Bearer secret-key"
    assert body["model"] == "some-model"
    assert body["response_format"]["json_schema"]["strict"] is True
    question = body["messages"][-1]["content"]
    told = ["Backend", "Data Engineer", "Backend Engineer Lead", "Rust Engineer", "Senior Engineer"]
    assert all(text in question for text in told)
    assert all(offer.description in question for offer in OFFERS)


def test_sends_the_start_and_the_end_of_a_long_description() -> None:
    # Arrange
    offers = [OfferText("Backend Engineer", "Acme", "START " + "x" * 20_000 + " END")]

    # Act
    _request, body = _sent(offers)

    # Assert
    question = body["messages"][-1]["content"]
    assert "START" in question
    assert "END" in question
    assert len(question) < 4_000


def test_leaves_out_the_offers_the_model_does_not_answer_for() -> None:
    # Arrange
    answer = {"offers": [{"offer": 1, "verdict": "ok", "why": "Fits."}, {"offer": 7}]}

    # Act
    reply = _triage(lambda _request: _completion(json.dumps(answer)))

    # Assert
    assert (reply.answers, reply.suggestions) == ({1: TriageAnswer("ok", "Fits.")}, [])


@pytest.mark.parametrize(
    "handler",
    [
        pytest.param(lambda _request: httpx2.Response(429, json={}), id="quota"),
        pytest.param(lambda _request: httpx2.Response(500, text="oops"), id="server-error"),
        pytest.param(lambda _request: httpx2.Response(200, text="not json"), id="not-json"),
        pytest.param(lambda _request: httpx2.Response(200, json={"choices": []}), id="no-choice"),
        pytest.param(lambda _request: _completion("not json"), id="answer-not-json"),
        pytest.param(lambda _request: _completion("[]"), id="answer-not-an-object"),
        pytest.param(lambda _request: _completion('{"offers": 3}'), id="offers-not-a-list"),
    ],
)
def test_fails_when_the_model_does_not_answer_what_was_asked(handler: Handler) -> None:
    # Act / Assert
    with pytest.raises(OfferTriagerError):
        _triage(handler)


def test_fails_when_the_model_cannot_be_reached() -> None:
    # Arrange
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("no network", request=request)

    # Act / Assert
    with pytest.raises(OfferTriagerError):
        _triage(handler)
