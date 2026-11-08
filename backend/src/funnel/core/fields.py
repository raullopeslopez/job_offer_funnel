"""Reusable field types for request schemas."""

from typing import Annotated

from pydantic import AfterValidator, Field, HttpUrl, TypeAdapter

_http_url = TypeAdapter(HttpUrl)


def _validate_http_url(value: str) -> str:
    # Validate as an http(s) URL but keep the user's text (HttpUrl would add a trailing slash).
    _http_url.validate_python(value)
    return value


HttpUrlText = Annotated[
    str, AfterValidator(_validate_http_url), Field(json_schema_extra={"format": "uri"})
]
