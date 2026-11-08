from pydantic import BaseModel, Field

from funnel.modules.applications.domain import Channel, Stage


class ConversionStepRead(BaseModel):
    from_stage: Stage
    to_stage: Stage = Field(description="The stage right after `from_stage`.")
    reached_from: int = Field(description="Applications that reached `from_stage` or later.")
    reached_to: int = Field(description="Applications that reached `to_stage` or later.")
    rate: float | None = Field(
        description="`reached_to` as a percentage of `reached_from`, with one decimal. "
        "Null when `reached_from` is 0.",
        examples=[66.7],
    )


class ConversionRead(BaseModel):
    steps: list[ConversionStepRead] = Field(description="One per pair of consecutive stages.")


class ChannelConversionRead(BaseModel):
    channel: Channel
    steps: list[ConversionStepRead]


class ConversionByChannelRead(BaseModel):
    channels: list[ChannelConversionRead] = Field(
        description="Only channels with applications, in the order of the `Channel` enum."
    )


class PipelineStageRead(BaseModel):
    stage: Stage
    applications: int


class PipelineRead(BaseModel):
    stages: list[PipelineStageRead] = Field(
        description="Every stage from `evaluated` to `offer`, including those with 0."
    )
    total: int
