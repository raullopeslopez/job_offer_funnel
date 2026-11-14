import pytest

from funnel.modules.inbox.domain import (
    DiscardReason,
    OfferText,
    SuggestedDiscard,
    Triage,
    TriageAnswer,
    Verdict,
    kept_suggestion,
    kept_triage,
)

pytestmark = pytest.mark.unit

OFFER = OfferText("Backend Engineer Lead", "Acme", "Go services. Part-time, 20 hours a week.")


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        pytest.param(
            TriageAnswer("ko", "Why.", "contract", "Part-time,  20 hours"),
            SuggestedDiscard(DiscardReason.CONTRACT, "Part-time, 20 hours"),
            id="sentence-of-the-description-spaces-aside",
        ),
        pytest.param(
            TriageAnswer("ko", "Why.", "title_word", " lead "),
            SuggestedDiscard(DiscardReason.TITLE_WORD, "lead"),
            id="word-of-the-title-ignoring-case",
        ),
        pytest.param(TriageAnswer("ok", "Fits."), None, id="ok"),
        pytest.param(
            TriageAnswer("ok", "Fits.", "contract", "Part-time, 20 hours"),
            None,
            id="ok-with-reason",
        ),
        pytest.param(
            TriageAnswer("ko", "Why.", "contract", "Full-time"), None, id="not-in-the-description"
        ),
        pytest.param(TriageAnswer("ko", "Why.", "stack", None), None, id="without-evidence"),
        pytest.param(TriageAnswer("ko", "Why.", "title_word", "Lea"), None, id="part-of-a-word"),
        pytest.param(
            TriageAnswer("ko", "Why.", "title_word", "Go"), None, id="word-of-the-description"
        ),
        pytest.param(TriageAnswer("ko", "Why.", "none", "Go services"), None, id="reason-none"),
        pytest.param(
            TriageAnswer("ko", "Why.", "expired", "Go services"), None, id="reason-expired"
        ),
        pytest.param(
            TriageAnswer("ko", "Why.", "salary", "Go services"), None, id="unknown-reason"
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
            TriageAnswer("ok", " Fits  well. "), Triage(Verdict.OK, "Fits well."), id="ok"
        ),
        pytest.param(
            TriageAnswer("KO", "Crypto."), Triage(Verdict.KO, "Crypto."), id="ko-any-case"
        ),
        pytest.param(TriageAnswer("ok", "w" * 250), Triage(Verdict.OK, "w" * 200), id="why-cut"),
        pytest.param(TriageAnswer("ok", None), Triage(Verdict.OK, ""), id="no-why"),
        pytest.param(TriageAnswer(None, "Fits."), None, id="no-verdict"),
        pytest.param(TriageAnswer("maybe", "Fits."), None, id="unknown-verdict"),
    ],
)
def test_keeps_the_verdict_and_why(answer: TriageAnswer, expected: Triage | None) -> None:
    # Act
    kept = kept_triage(answer)

    # Assert
    assert kept == expected
