import importlib.util
import io
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError

import pytest

SCRIPT = Path(__file__).parents[3] / "scripts" / "import_offers.py"
spec = importlib.util.spec_from_file_location("import_offers", SCRIPT)
assert spec
assert spec.loader
import_offers = importlib.util.module_from_spec(spec)
sys.modules["import_offers"] = import_offers
spec.loader.exec_module(import_offers)


def _http_error(status: int, body: str) -> HTTPError:
    return HTTPError("http://api", status, "error", {}, io.BytesIO(body.encode()))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("error", "worked"),
    [
        (_http_error(429, '{"type":"/problems/import-too-soon"}'), True),
        (_http_error(502, '{"type":"/problems/feed-unavailable"}'), True),
        (_http_error(502, '{"type":"/problems/board-unavailable"}'), True),
        (_http_error(502, "Bad Gateway"), False),
        (_http_error(500, '{"type":"/problems/internal-error"}'), False),
        (URLError("connection refused"), False),
    ],
)
def test_import_from_counts_unavailable_sources_as_skipped(
    monkeypatch: pytest.MonkeyPatch, error: Exception, worked: bool
) -> None:
    # Arrange
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise error

    monkeypatch.setattr(import_offers, "call", fail)

    # Act
    result = import_offers.import_from("job board X", "http://api/x")

    # Assert
    assert result is worked
