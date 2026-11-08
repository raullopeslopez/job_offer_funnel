import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def test_health_reports_ok_when_database_is_reachable(client: TestClient) -> None:
    # Act
    response = client.get("/health")

    # Assert
    assert (response.status_code, response.json()) == (200, {"status": "ok"})
