import pytest

from funnel.modules.inbox.domain import CriteriaPreview, FitChange, OfferStatus, preview_criteria

PENDING, PROMOTED, DISCARDED = OfferStatus.PENDING, OfferStatus.PROMOTED, OfferStatus.DISCARDED


@pytest.mark.unit
def test_counts_only_the_offers_whose_fit_changes() -> None:
    # Arrange
    changes = [
        FitChange(PENDING, fits_now=False, fits_after=True, offers=2),
        FitChange(PENDING, fits_now=True, fits_after=False, offers=3),
        FitChange(PENDING, fits_now=True, fits_after=True, offers=7),
        FitChange(PROMOTED, fits_now=True, fits_after=False, offers=1),
        FitChange(PROMOTED, fits_now=False, fits_after=True, offers=5),
        FitChange(DISCARDED, fits_now=True, fits_after=False, offers=4),
        FitChange(DISCARDED, fits_now=False, fits_after=False, offers=9),
        FitChange(DISCARDED, fits_now=False, fits_after=True, offers=6),
    ]

    # Act
    preview = preview_criteria(changes)

    # Assert
    assert preview == CriteriaPreview(
        entering_pending=2,
        leaving_pending=3,
        promoted_filtered=1,
        discarded_filtered=4,
        discarded_fitting=6,
    )
