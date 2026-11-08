import pytest
from fastapi.testclient import TestClient
from support.probe import build_probe_app


@pytest.fixture
def probe_client() -> TestClient:
    # Unexpected errors must come back as responses, as a real client would see them.
    return TestClient(build_probe_app(), raise_server_exceptions=False)
