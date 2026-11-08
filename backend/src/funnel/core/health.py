from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from funnel.core.db import SessionDep

router = APIRouter(tags=["health"])


class HealthRead(BaseModel):
    status: str


@router.get("/health")
async def read_health(session: SessionDep) -> HealthRead:
    """Public liveness check that also verifies the database connection."""
    await session.execute(text("SELECT 1"))
    return HealthRead(status="ok")
