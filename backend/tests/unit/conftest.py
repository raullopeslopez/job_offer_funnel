import pytest
from fastapi.testclient import TestClient
from support.probe import build_probe_app


@pytest.fixture
def probe_client() -> TestClient:
    return TestClient(build_probe_app())
