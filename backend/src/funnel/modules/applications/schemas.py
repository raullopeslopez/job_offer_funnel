from datetime import date
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from funnel.modules.applications.domain import Outcome, Stage


class ApplicationRead(BaseModel):
    id: UUID
    stage: Stage = Field(description="Current stage; for a closed application, the stage reached.")
    outcome: Outcome | None = Field(description="Set when the application is closed.")


class TransitionCreate(BaseModel):
    """Move to a stage or close with an outcome: exactly one of `to_stage` and `outcome`."""

    to_stage: Stage | None = None
    outcome: Outcome | None = None
    occurred_on: date | None = Field(default=None, description="Defaults to today.")
    note: str | None = None

    @model_validator(mode="after")
    def _require_stage_or_outcome(self) -> Self:
        if (self.to_stage is None) == (self.outcome is None):
            msg = "provide exactly one of to_stage or outcome"
            raise ValueError(msg)
        return self


class TransitionRead(BaseModel):
    from_stage: Stage | None = Field(description="Null for the application's first stage.")
    to_stage: Stage = Field(description="Equals from_stage when the transition closes it.")
    outcome: Outcome | None
    occurred_on: date
    note: str | None
