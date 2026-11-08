from datetime import date, datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

from funnel.core.fields import HttpUrlText
from funnel.modules.applications.domain import Channel, Outcome, Priority, Stage

Role = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
PostingUrl = Annotated[HttpUrlText, Field(examples=["https://acme.example/jobs/1"])]
# Mirrors STARTING_STAGES in the domain, so the contract lists the allowed values.
StartingStage = Literal[Stage.EVALUATED, Stage.APPLIED]


class ApplicationCreate(BaseModel):
    company_id: UUID
    role: Role
    channel: Channel
    priority: Priority | None = None
    url: PostingUrl | None = None
    notes: str | None = None
    stage: StartingStage = Field(default=Stage.EVALUATED, description="The first stage.")
    occurred_on: date | None = Field(
        default=None, description="When it entered the first stage. Defaults to today."
    )


class ApplicationUpdate(BaseModel):
    """Partial update: only the fields sent change. `null` clears an optional field."""

    company_id: UUID | None = None
    role: Role | None = None
    channel: Channel | None = None
    priority: Priority | None = None
    url: PostingUrl | None = None
    notes: str | None = None

    @field_validator("company_id", "role", "channel")
    @classmethod
    def _reject_clearing_required(cls, value: object) -> object:
        # Runs only for fields sent in the body, so omitting one stays valid.
        if value is None:
            msg = "is required and cannot be cleared"
            raise ValueError(msg)
        return value


class ApplicationFilters(BaseModel):
    stage: Stage | None = Field(
        default=None, description="Current stage; for a closed application, the stage reached."
    )
    outcome: Outcome | None = None
    channel: Channel | None = None
    active: bool | None = Field(
        default=None, description="`true`: still open (no outcome). `false`: closed."
    )


class ApplicationRead(BaseModel):
    id: UUID
    company_id: UUID
    role: str
    channel: Channel
    priority: Priority | None
    url: str | None
    notes: str | None
    stage: Stage = Field(description="Current stage; for a closed application, the stage reached.")
    outcome: Outcome | None = Field(description="Set when the application is closed.")
    created_at: datetime


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


class ApplicationDetailRead(ApplicationRead):
    transitions: list[TransitionRead] = Field(description="Transition history, oldest first.")
