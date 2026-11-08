import pytest
from fastapi.testclient import TestClient
from support.probe import PROBE_TOKEN

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("headers", "expected_status"),
    [
        pytest.param({}, 401, id="missing-token"),
        pytest.param({"Authorization": "Bearer wrong-token"}, 401, id="wrong-token"),
        pytest.param({"Authorization": PROBE_TOKEN}, 401, id="missing-bearer-scheme"),
        pytest.param({"Authorization": f"Bearer {PROBE_TOKEN}"}, 200, id="valid-token"),
    ],
)
def test_protected_route_requires_valid_bearer_token(
    probe_client: TestClient, headers: dict[str, str], expected_status: int
) -> None:
    # Act
    response = probe_client.get("/probe/protected", headers=headers)

    # Assert
    assert response.status_code == expected_status


def test_rejected_token_returns_unauthorized_problem(probe_client: TestClient) -> None:
    # Act
    response = probe_client.get("/probe/protected")

    # Assert
    assert response.json()["type"] == "/problems/unauthorized"
