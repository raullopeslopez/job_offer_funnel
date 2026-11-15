import pytest

from funnel.modules.inbox.domain import (
    Confidence,
    DiscardReason,
    OfferText,
    SuggestedDiscard,
    Triage,
    TriageAnswer,
    Verdict,
    Why,
    kept_suggestion,
    kept_triage,
)

pytestmark = pytest.mark.unit

OFFER = OfferText("Backend Engineer Lead", "Acme", "Go services. Part-time, 20 hours a week.")


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        pytest.param(
            TriageAnswer("ko", why_not="Why.", reason="contract", evidence="Part-time,  20 hours"),
            SuggestedDiscard(DiscardReason.CONTRACT, "Part-time, 20 hours"),
            id="sentence-of-the-description-spaces-aside",
        ),
        pytest.param(
            TriageAnswer("ko", why_not="Why.", reason="title_word", evidence=" lead "),
            SuggestedDiscard(DiscardReason.TITLE_WORD, "lead"),
            id="word-of-the-title-ignoring-case",
        ),
        pytest.param(TriageAnswer("ok", "Fits."), None, id="ok"),
        pytest.param(
            TriageAnswer("ok", "Fits.", reason="contract", evidence="Part-time, 20 hours"),
            None,
            id="ok-with-reason",
        ),
        pytest.param(
            TriageAnswer("ko", why_not="Why.", reason="contract", evidence="Full-time"),
            None,
            id="not-in-the-description",
        ),
        pytest.param(
            TriageAnswer("ko", why_not="Why.", reason="stack", evidence=None),
            None,
            id="without-evidence",
        ),
        pytest.param(
            TriageAnswer("ko", why_not="Why.", reason="title_word", evidence="Lea"),
            None,
            id="part-of-a-word",
        ),
        pytest.param(
            TriageAnswer("ko", why_not="Why.", reason="title_word", evidence="Go"),
            None,
            id="word-of-the-description",
        ),
        pytest.param(
            TriageAnswer("ko", why_not="Why.", reason="none", evidence="Go services"),
            None,
            id="reason-none",
        ),
        pytest.param(
            TriageAnswer("ko", why_not="Why.", reason="expired", evidence="Go services"),
            None,
            id="reason-expired",
        ),
        pytest.param(
            TriageAnswer("ko", why_not="Why.", reason="salary", evidence="Go services"),
            None,
            id="unknown-reason",
        ),
    ],
)
def test_keeps_only_suggestions_whose_evidence_holds(
    answer: TriageAnswer, expected: SuggestedDiscard | None
) -> None:
    # Act
    kept = kept_suggestion(answer, OFFER)

    # Assert
    assert kept == expected


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        pytest.param(
            TriageAnswer("ok", " Fits  well. ", "Crypto.", confidence="high"),
            Triage(Verdict.OK, Why("Fits well."), Why("Crypto."), Confidence.HIGH),
            id="both-sides",
        ),
        pytest.param(
            TriageAnswer("KO", why_not="Part-time.", confidence="LOW"),
            Triage(Verdict.KO, None, Why("Part-time."), Confidence.LOW),
            id="ko-any-case",
        ),
        pytest.param(
            TriageAnswer("ok", "w" * 250, "n" * 250),
            Triage(Verdict.OK, Why("w" * 200), Why("n" * 200)),
            id="whys-cut",
        ),
        pytest.param(TriageAnswer("ok", None, "  "), Triage(Verdict.OK), id="nothing-to-say"),
        pytest.param(
            TriageAnswer("ok", "Fits.", confidence="sure"),
            Triage(Verdict.OK, Why("Fits.")),
            id="unknown-confidence",
        ),
        pytest.param(TriageAnswer(None, "Fits."), None, id="no-verdict"),
        pytest.param(TriageAnswer("maybe", "Fits."), None, id="unknown-verdict"),
    ],
)
def test_keeps_the_verdict_whys_and_confidence(
    answer: TriageAnswer, expected: Triage | None
) -> None:
    # Act
    kept = kept_triage(answer, OFFER)

    # Assert
    assert kept == expected


@pytest.mark.parametrize(
    ("quote", "kept"),
    [
        pytest.param("Backend Engineer", "Backend Engineer", id="from-the-title"),
        pytest.param("Part-time,  20 hours", "Part-time, 20 hours", id="from-the-description"),
        pytest.param("Go services in Rust", None, id="not-in-the-offer"),
        pytest.param("go services", None, id="other-case"),
        pytest.param(None, None, id="no-quote"),
    ],
)
def test_keeps_a_quote_only_if_the_offer_says_it(quote: str | None, kept: str | None) -> None:
    # Act
    triage = kept_triage(TriageAnswer("ko", why_not="Part-time.", quote_not=quote), OFFER)

    # Assert
    assert triage is not None
    assert triage.why_not == Why("Part-time.", kept)
