"""Direct SQL over the applications table, referenced by name (no ORM models imported)."""

from sqlalchemy.ext.asyncio import AsyncSession

from funnel.modules.metrics.schemas import ConversionByChannelRead, ConversionRead, PipelineRead


async def conversion(session: AsyncSession) -> ConversionRead:
    raise NotImplementedError


async def conversion_by_channel(session: AsyncSession) -> ConversionByChannelRead:
    raise NotImplementedError


async def pipeline(session: AsyncSession) -> PipelineRead:
    raise NotImplementedError
