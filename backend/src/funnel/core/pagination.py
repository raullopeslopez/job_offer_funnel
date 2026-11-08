"""Collection convention: offset pagination and one envelope for every list endpoint."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Query
from pydantic import BaseModel

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


@dataclass(frozen=True)
class PageParams:
    limit: int
    offset: int


def get_page_params(
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PageParams:
    return PageParams(limit=limit, offset=offset)


class Page[ItemT](BaseModel):
    items: list[ItemT]
    total: int
    limit: int
    offset: int
