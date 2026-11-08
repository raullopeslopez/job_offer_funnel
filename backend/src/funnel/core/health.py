from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from funnel.core.db import get_session

router = APIRouter(tags=["health"])


class HealthRead(BaseModel):
    status: str


@router.get("/health")
async def read_health(session: Annotated[AsyncSession, Depends(get_session)]) -> HealthRead:
    """Public liveness check that also verifies the database connection."""
    await session.execute(text("SELECT 1"))
    return HealthRead(status="ok")
