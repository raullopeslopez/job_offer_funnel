import pytest

from funnel.modules.inbox.domain import (
    DiscardReason,
    OfferText,
    SuggestedDiscard,
    TriageAnswer,
    kept_suggestion,
)

pytestmark = pytest.mark.unit

OFFER = OfferText("Backend Engineer Lead", "Acme", "Go services. Part-time, 20 hours a week.")


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        pytest.param(
            TriageAnswer("contract", "Part-time,  20 hours"),
            SuggestedDiscard(DiscardReason.CONTRACT, "Part-time, 20 hours"),
            id="sentence-of-the-description-spaces-aside",
        ),
        pytest.param(
            TriageAnswer("title_word", " lead "),
            SuggestedDiscard(DiscardReason.TITLE_WORD, "lead"),
            id="word-of-the-title-ignoring-case",
        ),
        pytest.param(TriageAnswer(), None, id="nothing-to-say"),
        pytest.param(TriageAnswer("contract", "Full-time"), None, id="not-in-the-description"),
        pytest.param(TriageAnswer("stack", None), None, id="without-evidence"),
        pytest.param(TriageAnswer("title_word", "Lea"), None, id="part-of-a-word"),
        pytest.param(TriageAnswer("title_word", "Go"), None, id="word-of-the-description"),
        pytest.param(TriageAnswer("none", "Go services"), None, id="reason-none"),
        pytest.param(TriageAnswer("expired", "Go services"), None, id="reason-expired"),
        pytest.param(TriageAnswer("salary", "Go services"), None, id="unknown-reason"),
    ],
)
def test_keeps_only_suggestions_whose_evidence_holds(
    answer: TriageAnswer, expected: SuggestedDiscard | None
) -> None:
    # Act
    kept = kept_suggestion(answer, OFFER)

    # Assert
    assert kept == expected
