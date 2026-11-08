"""Direct SQL over the applications table, referenced by name (no ORM models imported).

The database groups the applications; turning counts per stage into the funnel
(applications that reached each stage, and the rate between stages) is plain Python.
"""

from collections import defaultdict
from collections.abc import Mapping
from decimal import ROUND_HALF_UP, Decimal
from itertools import pairwise
from typing import Final

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from funnel.modules.applications.domain import Channel, Stage
from funnel.modules.metrics.schemas import (
    ChannelConversionRead,
    ConversionByChannelRead,
    ConversionRead,
    ConversionStepRead,
    PipelineRead,
    PipelineStageRead,
)

# Accepted applications have no outcome, but their process is over.
PIPELINE_STAGES: Final = [stage for stage in Stage if stage is not Stage.ACCEPTED]

_ONE_DECIMAL = Decimal("0.1")

_COUNT_BY_STAGE = text("SELECT stage, count(*) FROM applications GROUP BY stage")
_COUNT_BY_CHANNEL_AND_STAGE = text(
    "SELECT channel, stage, count(*) FROM applications GROUP BY channel, stage"
)
_COUNT_IN_PROGRESS_BY_STAGE = text(
    "SELECT stage, count(*) FROM applications"
    " WHERE outcome IS NULL AND stage <> :accepted GROUP BY stage"
)


async def conversion(session: AsyncSession) -> ConversionRead:
    rows = await session.execute(_COUNT_BY_STAGE)
    counts = {Stage(stage): count for stage, count in rows}
    return ConversionRead(steps=conversion_steps(counts))


async def conversion_by_channel(session: AsyncSession) -> ConversionByChannelRead:
    rows = await session.execute(_COUNT_BY_CHANNEL_AND_STAGE)
    counts: defaultdict[Channel, dict[Stage, int]] = defaultdict(dict)
    for channel, stage, count in rows:
        counts[Channel(channel)][Stage(stage)] = count
    return ConversionByChannelRead(
        channels=[
            ChannelConversionRead(channel=channel, steps=conversion_steps(counts[channel]))
            for channel in Channel
            if channel in counts
        ]
    )


async def pipeline(session: AsyncSession) -> PipelineRead:
    rows = await session.execute(_COUNT_IN_PROGRESS_BY_STAGE, {"accepted": Stage.ACCEPTED})
    counts = {Stage(stage): count for stage, count in rows}
    stages = [
        PipelineStageRead(stage=stage, applications=counts.get(stage, 0))
        for stage in PIPELINE_STAGES
    ]
    return PipelineRead(stages=stages, total=sum(counts.values()))


def conversion_steps(counts: Mapping[Stage, int]) -> list[ConversionStepRead]:
    """Conversion between consecutive stages, from the applications currently in each stage."""
    reached: dict[Stage, int] = {}
    running_total = 0
    # An application in a stage has reached it and every earlier one.
    for stage in reversed(Stage):
        running_total += counts.get(stage, 0)
        reached[stage] = running_total
    return [
        ConversionStepRead(
            from_stage=current,
            to_stage=following,
            reached_from=reached[current],
            reached_to=reached[following],
            rate=_rate(reached[following], reached[current]),
        )
        for current, following in pairwise(Stage)
    ]


def _rate(part: int, whole: int) -> float | None:
    if whole == 0:
        return None
    # Decimal rounds half up (66.65 -> 66.7); float rounding would depend on binary noise.
    percentage = (Decimal(part) * 100 / Decimal(whole)).quantize(_ONE_DECIMAL, ROUND_HALF_UP)
    return float(percentage)
