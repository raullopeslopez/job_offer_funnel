from enum import StrEnum


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
