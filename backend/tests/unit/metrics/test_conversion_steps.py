import pytest

from funnel.modules.applications.domain import Stage
from funnel.modules.metrics.queries import conversion_steps

pytestmark = pytest.mark.unit


def test_an_application_reaches_its_stage_and_every_earlier_one() -> None:
    # Act
    steps = conversion_steps({Stage.INTERVIEWING: 1})

    # Assert
    assert [(step.reached_from, step.reached_to) for step in steps] == [
        (1, 1),
        (1, 1),
        (1, 1),
        (1, 0),
        (0, 0),
    ]


@pytest.mark.parametrize(
    ("in_from_stage", "in_later_stage", "expected"),
    [
        pytest.param(1, 2, 66.7, id="rounds-to-one-decimal"),
        pytest.param(2, 0, 0.0, id="none-converted"),
        pytest.param(0, 3, 100.0, id="all-converted"),
        pytest.param(1999, 1, 0.1, id="rounds-half-up"),
        pytest.param(0, 0, None, id="no-applications-no-rate"),
    ],
)
def test_conversion_rate(in_from_stage: int, in_later_stage: int, expected: float | None) -> None:
    # Arrange
    counts = {Stage.EVALUATED: in_from_stage, Stage.APPLIED: in_later_stage}

    # Act
    first_step = conversion_steps(counts)[0]

    # Assert
    assert first_step.rate == expected
