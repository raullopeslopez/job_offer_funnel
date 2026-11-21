import asyncio
import runpy
from pathlib import Path
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient


def test_import_one_profile_twice(
    client: TestClient, database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    client.post(
        "/api/v1/search-profiles", json={"name": "Other", "titles": ["Designer"]}
    ).raise_for_status()
    client.post(
        "/api/v1/search-profiles",
        json={"name": "London", "titles": ["Engineer"], "location": "London"},
    ).raise_for_status()
    client.post(
        "/api/v1/job-boards",
        json={
            "name": "Adzuna",
            "syntax": "keywords",
            "search_url_template": "https://example.com/?q={query}",
        },
    ).raise_for_status()
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ADZUNA_PROFILE", "London")
    monkeypatch.setenv("ADZUNA_APP_ID", "test-id")
    monkeypatch.setenv("ADZUNA_APP_KEY", "test-key")
    job = {
        "title": "Engineer",
        "company": {"display_name": "Example"},
        "location": {"display_name": "London"},
        "description": "Python",
        "redirect_url": "https://www.adzuna.co.uk/jobs/details/123",
    }

    def search(request: httpx2.Request) -> httpx2.Response:
        assert request.url.host == "api.adzuna.com"
        assert request.url.path == "/v1/api/jobs/gb/search/1"
        assert request.url.params["what"] == "Engineer"
        assert request.url.params["where"] == "London"
        assert request.url.params["app_key"] == "test-key"
        return httpx2.Response(200, json={"results": [job, job]})

    original = httpx2.AsyncClient

    def mock_client(**kwargs: Any) -> httpx2.AsyncClient:
        return original(transport=httpx2.MockTransport(search), **kwargs)

    monkeypatch.setattr(httpx2, "AsyncClient", mock_client)
    main = runpy.run_path(str(Path(__file__).parents[2] / "scripts" / "import_adzuna.py"))["main"]
    assert asyncio.run(main()) == 0
    assert asyncio.run(main()) == 0
    page = client.get("/api/v1/offers").json()
    assert page["total"] == 1
    assert page["items"][0]["job_board_name"] == "Adzuna"
    assert page["items"][0]["url"] == job["redirect_url"]
