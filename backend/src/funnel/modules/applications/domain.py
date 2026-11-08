"""Stage state machine of an application.

Source of truth: specs/applications/stage_transitions.feature.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from http import HTTPStatus
from typing import Final
from uuid import UUID

from funnel.core.exceptions import AppError, DomainError


class Stage(StrEnum):
    """Funnel stages, in order. `discovered` arrives with phase 0 (out of the MVP)."""

    EVALUATED = "evaluated"
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    ACCEPTED = "accepted"


class Outcome(StrEnum):
    """How a closed application ended. A closed application keeps the stage it reached."""

    REJECTED = "rejected"
    GHOSTED = "ghosted"
    WITHDRAWN = "withdrawn"
    OFFER_DECLINED = "offer_declined"


class Channel(StrEnum):
    """Where the application came from; used to measure conversion per channel."""

    PORTAL = "portal"
    REFERRAL = "referral"
    RECRUITER_INBOUND = "recruiter_inbound"
    DIRECT = "direct"
    NETWORKING = "networking"


class Priority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# An application enters the funnel before or right when applying.
STARTING_STAGES: Final = frozenset({Stage.EVALUATED, Stage.APPLIED})

_POSITION: Final[Mapping[Stage, int]] = {stage: index for index, stage in enumerate(Stage)}

_AFTER_APPLYING: Final = frozenset(
    {Stage.APPLIED, Stage.SCREENING, Stage.INTERVIEWING, Stage.OFFER}
)

# Stages from which an application can be closed with each outcome.
OUTCOME_STAGES: Final[Mapping[Outcome, frozenset[Stage]]] = {
    Outcome.WITHDRAWN: frozenset(Stage) - {Stage.ACCEPTED},
    Outcome.REJECTED: _AFTER_APPLYING,
    Outcome.GHOSTED: _AFTER_APPLYING,
    Outcome.OFFER_DECLINED: frozenset({Stage.OFFER}),
}

# Closed applications that can still move: back to their reached stage or later.
REACTIVATABLE_OUTCOMES: Final = frozenset({Outcome.GHOSTED})


class InvalidTransitionError(DomainError):
    slug = "invalid-transition"
    title = "Invalid transition"


class InvalidTransitionDateError(DomainError):
    slug = "invalid-transition-date"
    title = "Invalid transition date"
    status = HTTPStatus.UNPROCESSABLE_CONTENT


class UnknownCompanyError(AppError):
    """The company referenced in the request does not exist (422: the path itself is valid)."""

    slug = "unknown-company"
    title = "Unknown company"
    status = HTTPStatus.UNPROCESSABLE_CONTENT


@dataclass(frozen=True)
class StageChange:
    """A requested change: exactly one of `to_stage` (move) or `outcome` (close)."""

    to_stage: Stage | None = None
    outcome: Outcome | None = None
    occurred_on: date | None = None
    note: str | None = None


@dataclass(frozen=True)
class Transition:
    from_stage: Stage | None
    to_stage: Stage
    outcome: Outcome | None
    occurred_on: date
    note: str | None


def first_transition(stage: Stage, occurred_on: date | None, today: date) -> Transition:
    """The transition that brings a new application into the funnel; the date defaults to today."""
    if stage not in STARTING_STAGES:
        raise InvalidTransitionError(f"An application cannot start in {stage}")
    occurred_on = occurred_on or today
    if occurred_on > today:
        raise InvalidTransitionDateError(f"{occurred_on} is in the future")
    return Transition(
        from_stage=None, to_stage=stage, outcome=None, occurred_on=occurred_on, note=None
    )


@dataclass
class Application:
    id: UUID
    stage: Stage
    outcome: Outcome | None
    last_transition_on: date | None

    def apply(self, change: StageChange, today: date) -> Transition:
        """Validate and apply `change`; the date defaults to `today`."""
        occurred_on = change.occurred_on or today
        if change.outcome is not None:
            self._check_can_close(change.outcome)
        else:
            assert change.to_stage is not None
            self._check_can_move(change.to_stage)
        self._check_date(occurred_on, today)

        transition = Transition(
            from_stage=self.stage,
            to_stage=change.to_stage or self.stage,
            outcome=change.outcome,
            occurred_on=occurred_on,
            note=change.note,
        )
        self.stage = transition.to_stage
        self.outcome = transition.outcome
        self.last_transition_on = occurred_on
        return transition

    def _check_can_move(self, target: Stage) -> None:
        if self.outcome is not None and self.outcome not in REACTIVATABLE_OUTCOMES:
            raise InvalidTransitionError(f"Application is closed as {self.outcome}")
        # A reactivated application may stay in its reached stage; an open one must advance.
        lowest_allowed = _POSITION[self.stage] + (0 if self.outcome is not None else 1)
        if _POSITION[target] < lowest_allowed:
            raise InvalidTransitionError(f"Cannot move from {self.stage} to {target}")

    def _check_can_close(self, outcome: Outcome) -> None:
        if self.outcome is not None:
            raise InvalidTransitionError(f"Application is already closed as {self.outcome}")
        if self.stage not in OUTCOME_STAGES[outcome]:
            raise InvalidTransitionError(f"Cannot close as {outcome} from {self.stage}")

    def _check_date(self, occurred_on: date, today: date) -> None:
        if occurred_on > today:
            raise InvalidTransitionDateError(f"{occurred_on} is in the future")
        if self.last_transition_on is not None and occurred_on < self.last_transition_on:
            raise InvalidTransitionDateError(
                f"{occurred_on} is before the previous transition ({self.last_transition_on})"
            )
