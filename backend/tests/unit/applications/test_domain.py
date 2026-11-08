from datetime import date
from itertools import combinations, product
from uuid import uuid7

import pytest

from funnel.modules.applications.domain import (
    Application,
    InvalidTransitionDateError,
    InvalidTransitionError,
    Outcome,
    Stage,
    StageChange,
    Transition,
)

pytestmark = pytest.mark.unit

TODAY = date(2026, 3, 10)
ENTERED_ON = date(2026, 3, 1)

FORWARD_MOVES = list(combinations(Stage, 2))
BACKWARD_OR_SAME_MOVES = [(later, earlier) for earlier, later in FORWARD_MOVES] + [
    (stage, stage) for stage in Stage
]

# Copied from the spec: which outcomes may close an application in each stage.
ALLOWED_CLOSURES = [
    *[(stage, Outcome.WITHDRAWN) for stage in Stage if stage is not Stage.ACCEPTED],
    *[
        (stage, outcome)
        for outcome in (Outcome.REJECTED, Outcome.GHOSTED)
        for stage in (Stage.APPLIED, Stage.SCREENING, Stage.INTERVIEWING, Stage.OFFER)
    ],
    (Stage.OFFER, Outcome.OFFER_DECLINED),
]
DISALLOWED_CLOSURES = [pair for pair in product(Stage, Outcome) if pair not in ALLOWED_CLOSURES]

FINAL_OUTCOMES = [Outcome.REJECTED, Outcome.WITHDRAWN, Outcome.OFFER_DECLINED]


def make_application(
    stage: Stage, outcome: Outcome | None = None, last_transition_on: date = ENTERED_ON
) -> Application:
    return Application(
        id=uuid7(), stage=stage, outcome=outcome, last_transition_on=last_transition_on
    )


# --- Moving ---


@pytest.mark.parametrize(("current", "target"), FORWARD_MOVES, ids=str)
def test_moving_forward_changes_stage_and_keeps_application_open(
    current: Stage, target: Stage
) -> None:
    # Arrange
    application = make_application(current)

    # Act
    application.apply(StageChange(to_stage=target), TODAY)

    # Assert
    assert (application.stage, application.outcome) == (target, None)


@pytest.mark.parametrize(("current", "target"), BACKWARD_OR_SAME_MOVES, ids=str)
def test_moving_back_or_to_the_same_stage_is_rejected(current: Stage, target: Stage) -> None:
    # Arrange
    application = make_application(current)

    # Act / Assert
    with pytest.raises(InvalidTransitionError):
        application.apply(StageChange(to_stage=target), TODAY)


def test_rejected_move_leaves_application_unchanged() -> None:
    # Arrange
    application = make_application(Stage.SCREENING)

    # Act
    with pytest.raises(InvalidTransitionError):
        application.apply(StageChange(to_stage=Stage.APPLIED), TODAY)

    # Assert
    assert (application.stage, application.outcome) == (Stage.SCREENING, None)


# --- Closing ---


@pytest.mark.parametrize(("stage", "outcome"), ALLOWED_CLOSURES, ids=str)
def test_closing_with_allowed_outcome_keeps_reached_stage(stage: Stage, outcome: Outcome) -> None:
    # Arrange
    application = make_application(stage)

    # Act
    application.apply(StageChange(outcome=outcome), TODAY)

    # Assert
    assert (application.stage, application.outcome) == (stage, outcome)


@pytest.mark.parametrize(("stage", "outcome"), DISALLOWED_CLOSURES, ids=str)
def test_closing_with_outcome_not_allowed_in_stage_is_rejected(
    stage: Stage, outcome: Outcome
) -> None:
    # Arrange
    application = make_application(stage)

    # Act / Assert
    with pytest.raises(InvalidTransitionError):
        application.apply(StageChange(outcome=outcome), TODAY)


def test_closing_records_a_transition_that_stays_in_the_reached_stage() -> None:
    # Arrange
    application = make_application(Stage.SCREENING)

    # Act
    transition = application.apply(StageChange(outcome=Outcome.GHOSTED, note="No reply"), TODAY)

    # Assert
    assert transition == Transition(
        from_stage=Stage.SCREENING,
        to_stage=Stage.SCREENING,
        outcome=Outcome.GHOSTED,
        occurred_on=TODAY,
        note="No reply",
    )


# --- Closed applications ---


@pytest.mark.parametrize(
    ("outcome", "change"),
    [
        *[
            pytest.param(outcome, StageChange(to_stage=Stage.OFFER), id=f"{outcome}-move")
            for outcome in FINAL_OUTCOMES
        ],
        *[
            pytest.param(outcome, StageChange(outcome=Outcome.WITHDRAWN), id=f"{outcome}-close")
            for outcome in [*FINAL_OUTCOMES, Outcome.GHOSTED]
        ],
    ],
)
def test_closed_application_rejects_changes_except_ghosted_reactivation(
    outcome: Outcome, change: StageChange
) -> None:
    # Arrange
    application = make_application(Stage.INTERVIEWING, outcome=outcome)

    # Act / Assert
    with pytest.raises(InvalidTransitionError):
        application.apply(change, TODAY)


@pytest.mark.parametrize("target", [Stage.SCREENING, Stage.INTERVIEWING, Stage.ACCEPTED], ids=str)
def test_ghosted_application_reactivates_in_reached_stage_or_later(target: Stage) -> None:
    # Arrange
    application = make_application(Stage.SCREENING, outcome=Outcome.GHOSTED)

    # Act
    application.apply(StageChange(to_stage=target), TODAY)

    # Assert
    assert (application.stage, application.outcome) == (target, None)


@pytest.mark.parametrize("target", [Stage.EVALUATED, Stage.APPLIED], ids=str)
def test_ghosted_application_cannot_reactivate_before_reached_stage(target: Stage) -> None:
    # Arrange
    application = make_application(Stage.SCREENING, outcome=Outcome.GHOSTED)

    # Act / Assert
    with pytest.raises(InvalidTransitionError):
        application.apply(StageChange(to_stage=target), TODAY)


# --- Dates ---


@pytest.mark.parametrize(
    ("requested", "expected"),
    [
        pytest.param(None, TODAY, id="defaults-to-today"),
        pytest.param(date(2026, 3, 4), date(2026, 3, 4), id="past-date"),
        pytest.param(ENTERED_ON, ENTERED_ON, id="same-day-as-previous"),
    ],
)
def test_transition_date(requested: date | None, expected: date) -> None:
    # Arrange
    application = make_application(Stage.APPLIED)

    # Act
    transition = application.apply(
        StageChange(to_stage=Stage.SCREENING, occurred_on=requested), TODAY
    )

    # Assert
    assert transition.occurred_on == expected


@pytest.mark.parametrize(
    "requested",
    [
        pytest.param(date(2026, 3, 11), id="future"),
        pytest.param(date(2026, 2, 28), id="before-previous-transition"),
    ],
)
def test_invalid_transition_date_is_rejected(requested: date) -> None:
    # Arrange
    application = make_application(Stage.APPLIED)

    # Act / Assert
    with pytest.raises(InvalidTransitionDateError):
        application.apply(StageChange(to_stage=Stage.SCREENING, occurred_on=requested), TODAY)
