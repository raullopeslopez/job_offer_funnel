from fastapi import APIRouter

from funnel.core.db import SessionDep
from funnel.modules.metrics import queries
from funnel.modules.metrics.schemas import ConversionByChannelRead, ConversionRead, PipelineRead

router = APIRouter(prefix="/metrics", tags=["metrics"])

Session = SessionDep


@router.get("/conversion")
async def read_conversion(session: Session) -> ConversionRead:
    """Conversion from each stage to the next one, over every application.

    An application reached a stage when its stage is that one or a later one; closed
    applications count up to the stage they reached, and open ones count too.
    """
    return await queries.conversion(session)


@router.get("/conversion-by-channel")
async def read_conversion_by_channel(session: Session) -> ConversionByChannelRead:
    """The same conversion, for each channel with applications."""
    return await queries.conversion_by_channel(session)


@router.get("/pipeline")
async def read_pipeline(session: Session) -> PipelineRead:
    """Applications in progress per stage: no outcome and not accepted.

    Unlike the `active` filter of the application list (no outcome), it leaves out
    accepted applications, whose process is over.
    """
    return await queries.pipeline(session)
