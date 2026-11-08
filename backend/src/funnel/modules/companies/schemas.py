from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from funnel.core.fields import HttpUrlText

CompanyName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Website = Annotated[HttpUrlText, Field(examples=["https://acme.example"])]


class CompanyCreate(BaseModel):
    name: CompanyName
    website: Website | None = None


class CompanyRead(BaseModel):
    id: UUID
    name: str
    website: str | None
