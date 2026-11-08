from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, Field, HttpUrl, StringConstraints, TypeAdapter

_http_url = TypeAdapter(HttpUrl)


def _validate_website(value: str) -> str:
    # Validate as an http(s) URL but keep the user's text (HttpUrl would add a trailing slash).
    _http_url.validate_python(value)
    return value


CompanyName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Website = Annotated[
    str,
    AfterValidator(_validate_website),
    Field(json_schema_extra={"format": "uri"}, examples=["https://acme.example"]),
]


class CompanyCreate(BaseModel):
    name: CompanyName
    website: Website | None = None


class CompanyRead(BaseModel):
    id: UUID
    name: str
    website: str | None
