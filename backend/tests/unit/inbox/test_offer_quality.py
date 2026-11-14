from datetime import date, timedelta
from typing import Any

import pytest

from funnel.modules.applications.domain import Stage
from funnel.modules.inbox.domain import (
    DiscardReason,
    OfferStatus,
    QualityOffer,
    Review,
    Rule,
    Verdict,
    offer_quality,
    rate,
)

TODAY = date(2026, 3, 10)


def _offer(
    days_ago: int, status: OfferStatus = OfferStatus.PENDING, **fields: object
) -> QualityOffer:
    return QualityOffer(
        added_on=TODAY - timedelta(days=days_ago),
        status=status,
        is_imported=True,
        fits=True,
        **fields,  # type: ignore[arg-type]
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("part", "whole", "expected"),
    [
        pytest.param(1, 3, 33.3, id="one-decimal"),
        pytest.param(2, 3, 66.7, id="half-up"),
        pytest.param(0, 0, None, id="nothing-to-divide-by"),
    ],
)
def test_rate_is_a_percentage_with_one_decimal(
    part: int, whole: int, expected: float | None
) -> None:
    # Act
    result = rate(part, whole)

    # Assert
    assert result == expected


@pytest.mark.unit
def test_offers_count_in_the_week_they_were_added_within_the_4_weeks() -> None:
    # Arrange
    offers = [_offer(0), _offer(6), _offer(7), _offer(27), _offer(28)]

    # Act
    quality = offer_quality(offers, TODAY, near_misses_left=0)

    # Assert
    assert quality.starts_on == date(2026, 2, 11)
    assert [figures.fitting for _, figures in quality.weeks] == [1, 0, 1, 2]
    assert (quality.total.fitting, quality.fitting_per_week) == (4, 1.0)


@pytest.mark.unit
def test_precision_leaves_out_rescues_and_expired_offers() -> None:
    # Arrange
    offers = [
        _offer(1, OfferStatus.PROMOTED),
        _offer(1, OfferStatus.PROMOTED, review=Review.RESCUED, review_rules=[Rule.KEYWORDS]),
        _offer(1, OfferStatus.DISCARDED, discard_reason=DiscardReason.STACK),
        _offer(1, OfferStatus.DISCARDED, discard_reason=DiscardReason.EXPIRED),
    ]

    # Act
    quality = offer_quality(offers, TODAY, near_misses_left=0)

    # Assert
    total = quality.total
    assert (total.precision, total.decided, total.promoted) == (50.0, 2, 2)
    assert (total.losses, total.reviewed_near_misses) == (100.0, 1)
    assert quality.discard_reasons == [(DiscardReason.STACK, 1)]


@pytest.mark.unit
def test_reviews_that_were_not_near_misses_do_not_count_in_the_losses() -> None:
    # Arrange
    offers = [
        _offer(1, OfferStatus.PROMOTED, review=Review.RESCUED, review_rules=[Rule.TITLE]),
        _offer(1, review=Review.RIGHTLY_FILTERED, review_rules=[Rule.STABLE, Rule.KEYWORDS]),
    ]

    # Act
    quality = offer_quality(offers, TODAY, near_misses_left=3)

    # Assert
    assert (quality.total.losses, quality.near_misses_left) == (None, 3)


@pytest.mark.unit
def test_real_result_counts_the_stages_reached_by_the_promoted_offers() -> None:
    # Arrange
    offers = [
        _offer(1, OfferStatus.PROMOTED, stage=Stage.EVALUATED),
        _offer(1, OfferStatus.PROMOTED, stage=Stage.APPLIED),
        _offer(1, OfferStatus.PROMOTED, stage=Stage.INTERVIEWING),
    ]

    # Act
    quality = offer_quality(offers, TODAY, near_misses_left=0)

    # Assert
    total = quality.total
    assert (total.promoted, total.applied, total.answered) == (3, 2, 1)


@pytest.mark.unit
def test_the_triager_is_judged_by_what_was_done_with_the_triaged_offers() -> None:
    # Arrange
    suggested: dict[str, Any] = {"verdict": Verdict.KO, "suggested_discard": DiscardReason.STACK}
    offers = [
        _offer(1, OfferStatus.DISCARDED, discard_reason=DiscardReason.STACK, **suggested),
        _offer(1, OfferStatus.PROMOTED, **suggested),
        _offer(1, **suggested),
        _offer(1, OfferStatus.DISCARDED, discard_reason=DiscardReason.EXPIRED, **suggested),
        _offer(1, OfferStatus.DISCARDED, discard_reason=DiscardReason.LOCATION, verdict=Verdict.OK),
        _offer(1, OfferStatus.DISCARDED, discard_reason=DiscardReason.LOCATION),
    ]

    # Act
    quality = offer_quality(offers, TODAY, near_misses_left=0)

    # Assert
    total = quality.total
    assert (total.triager_precision, total.suggested_decided) == (50.0, 2)
    assert (total.triager_misses, total.triaged_discarded) == (50.0, 2)
