import pytest

from funnel.openapi import OPENAPI_PATH, render_openapi

pytestmark = pytest.mark.contract


def test_generated_openapi_matches_versioned_contract() -> None:
    # Act
    generated = render_openapi()

    # Assert
    assert generated == OPENAPI_PATH.read_text(encoding="utf-8"), (
        "API contract changed: run `just openapi` and review the diff of openapi.json"
    )
