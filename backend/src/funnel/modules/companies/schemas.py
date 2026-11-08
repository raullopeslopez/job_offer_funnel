from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, field_validator

from funnel.core.fields import HttpUrlText

CompanyName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Website = Annotated[HttpUrlText, Field(examples=["https://acme.example"])]


class CompanyCreate(BaseModel):
    name: CompanyName
    website: Website | None = None


class CompanyUpdate(BaseModel):
    """Partial update: only the fields sent change. `null` clears the website."""

    name: CompanyName | None = None
    website: Website | None = None

    @field_validator("name")
    @classmethod
    def _reject_clearing_name(cls, value: str | None) -> str:
        # Runs only when the name is sent, so omitting it stays valid.
        if value is None:
            msg = "is required and cannot be cleared"
            raise ValueError(msg)
        return value


class CompanyRead(BaseModel):
    id: UUID
    name: str
    website: str | None
