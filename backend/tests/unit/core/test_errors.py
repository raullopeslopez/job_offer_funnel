import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("name", "expected_problem"),
    [
        pytest.param(
            "domain",
            {
                "type": "/problems/domain-error",
                "title": "Business rule violated",
                "status": 409,
                "detail": "probe domain",
            },
            id="domain-error-is-409",
        ),
        pytest.param(
            "not-found",
            {
                "type": "/problems/not-found",
                "title": "Resource not found",
                "status": 404,
                "detail": "probe not-found",
            },
            id="not-found-is-404",
        ),
        pytest.param(
            "unauthorized",
            {
                "type": "/problems/unauthorized",
                "title": "Missing or invalid credentials",
                "status": 401,
                "detail": "probe unauthorized",
            },
            id="unauthorized-is-401",
        ),
    ],
)
def test_app_errors_are_rendered_as_problem_details(
    probe_client: TestClient, name: str, expected_problem: dict[str, object]
) -> None:
    # Act
    response = probe_client.get(f"/probe/errors/{name}")

    # Assert
    assert (response.status_code, response.json()) == (expected_problem["status"], expected_problem)


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("/probe/errors/domain", id="app-error"),
        pytest.param("/probe/items/not-a-number", id="validation-error"),
        pytest.param("/does-not-exist", id="unknown-route"),
    ],
)
def test_error_responses_use_problem_media_type(probe_client: TestClient, path: str) -> None:
    # Act
    response = probe_client.get(path)

    # Assert
    assert response.headers["content-type"] == "application/problem+json"


def test_validation_error_lists_invalid_fields(probe_client: TestClient) -> None:
    # Act
    response = probe_client.get("/probe/items/not-a-number")

    # Assert
    assert [error["loc"] for error in response.json()["errors"]] == [["path", "item_id"]]


def test_unknown_route_is_not_found_problem(probe_client: TestClient) -> None:
    # Act
    response = probe_client.get("/does-not-exist")

    # Assert
    assert response.json() == {"type": "/problems/not-found", "title": "Not Found", "status": 404}
