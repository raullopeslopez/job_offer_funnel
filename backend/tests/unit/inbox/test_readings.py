import pytest

from funnel.modules.discovery.domain import WorkMode
from funnel.modules.inbox.domain import Reading, plain_text, supported

pytestmark = pytest.mark.unit

TEXT = "Fully remote. Hiring across Europe. Full-time, permanent position."
ANSWER = Reading(
    work_mode=WorkMode.REMOTE,
    work_mode_evidence="Fully remote",
    admits_location=True,
    admits_location_evidence="Hiring across Europe",
    stable=True,
    stable_evidence="Full-time, permanent",
)


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        pytest.param("<p>Fully <b>remote</b>.</p>", "Fully remote .", id="tags"),
        pytest.param("R&amp;D team,&nbsp;remote", "R&D team, remote", id="entities"),
        pytest.param("Fully\n\n  remote\t.", "Fully remote .", id="spaces"),
        pytest.param("", "", id="empty"),
    ],
)
def test_plain_text_is_what_a_person_reads(description: str, expected: str) -> None:
    # Act / Assert
    assert plain_text(description) == expected


def test_answers_with_their_evidence_in_the_text_are_kept() -> None:
    # Act
    kept = supported(ANSWER, TEXT, asked_location=True)

    # Assert
    assert kept == ANSWER


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        pytest.param(
            Reading(work_mode=WorkMode.ONSITE, work_mode_evidence="Based in London"),
            Reading(),
            id="evidence-not-in-the-text",
        ),
        pytest.param(
            Reading(work_mode=WorkMode.REMOTE, work_mode_evidence="fully remote"),
            Reading(),
            id="evidence-in-another-case",
        ),
        pytest.param(Reading(stable=False), Reading(), id="answer-without-evidence"),
        pytest.param(Reading(stable=False, stable_evidence=" "), Reading(), id="blank-evidence"),
        pytest.param(
            Reading(stable_evidence="Full-time, permanent"), Reading(), id="evidence-without-answer"
        ),
        pytest.param(
            Reading(stable=True, stable_evidence="Full-time,\n  permanent"),
            Reading(stable=True, stable_evidence="Full-time, permanent"),
            id="evidence-with-other-spaces",
        ),
    ],
)
def test_only_answers_the_text_says_are_kept(answer: Reading, expected: Reading) -> None:
    # Act
    kept = supported(answer, TEXT, asked_location=True)

    # Assert
    assert kept == expected


def test_the_location_answer_is_dropped_when_no_location_was_asked() -> None:
    # Act
    kept = supported(ANSWER, TEXT, asked_location=False)

    # Assert
    assert (kept.admits_location, kept.admits_location_evidence) == (None, None)
    assert kept.work_mode is WorkMode.REMOTE
