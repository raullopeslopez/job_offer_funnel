"""Shared test infrastructure.

Postgres runs in a single testcontainers instance per test run:
- with xdist, the controller starts it and hands the URL to every worker;
- in serial runs it starts lazily on first use, so unit tests never need Docker.

Migrations run once into a template database; each worker clones its own database
from it. HTTP tests commit for real, so tables are truncated after each test.
"""

from collections.abc import Iterator

import pytest
from alembic import command
from fastapi.testclient import TestClient
from filelock import FileLock
from pydantic import SecretStr
from support.postgres import alembic_config, create_database, truncate_all_tables
from testcontainers.community.postgres import PostgresContainer

from funnel.core.config import Settings
from funnel.main import create_app

POSTGRES_IMAGE = "postgres:17-alpine"
TEMPLATE_DATABASE = "funnel_template"
TEST_TOKEN = "test-token"

_WORKERINPUT_URL = "funnel_postgres_server_url"
_container_key = pytest.StashKey[PostgresContainer]()
_server_url_key = pytest.StashKey[str]()


def _start_server() -> tuple[PostgresContainer, str]:
    container = PostgresContainer(POSTGRES_IMAGE, driver="asyncpg")
    container.start()
    server_url: str = container.get_connection_url()
    template_url = create_database(server_url, TEMPLATE_DATABASE)
    command.upgrade(alembic_config(template_url), "head")
    return container, server_url


def _is_xdist_controller(config: pytest.Config) -> bool:
    is_worker = hasattr(config, "workerinput")
    return not is_worker and bool(getattr(config.option, "numprocesses", None))


def pytest_configure(config: pytest.Config) -> None:
    if _is_xdist_controller(config):
        container, server_url = _start_server()
        config.stash[_container_key] = container
        config.stash[_server_url_key] = server_url


@pytest.hookimpl(optionalhook=True)
def pytest_configure_node(node: object) -> None:
    config: pytest.Config = node.config  # type: ignore[attr-defined]
    node.workerinput[_WORKERINPUT_URL] = config.stash[_server_url_key]  # type: ignore[attr-defined]


def pytest_unconfigure(config: pytest.Config) -> None:
    container = config.stash.get(_container_key, None)
    if container is not None:
        container.stop()


@pytest.fixture(scope="session")
def postgres_server_url(request: pytest.FixtureRequest) -> Iterator[str]:
    workerinput: dict[str, str] | None = getattr(request.config, "workerinput", None)
    if workerinput is not None:
        yield workerinput[_WORKERINPUT_URL]
        return
    container, server_url = _start_server()
    yield server_url
    container.stop()


@pytest.fixture(scope="session")
def database_url(
    postgres_server_url: str, worker_id: str, tmp_path_factory: pytest.TempPathFactory
) -> str:
    # Concurrent clones of the same template can collide; serialize them.
    lock_path = tmp_path_factory.getbasetemp().parent / "create_database.lock"
    with FileLock(str(lock_path)):
        return create_database(postgres_server_url, f"test_{worker_id}", TEMPLATE_DATABASE)


@pytest.fixture
def empty_database_url(postgres_server_url: str, worker_id: str) -> str:
    """A database with no migrations applied."""
    return create_database(postgres_server_url, f"empty_{worker_id}")


@pytest.fixture
def settings(database_url: str) -> Settings:
    return Settings(database_url=database_url, auth_token=SecretStr(TEST_TOKEN))


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    """Authenticated HTTP client against a real database."""
    headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
    with TestClient(create_app(settings), headers=headers) as test_client:
        yield test_client
    truncate_all_tables(settings.database_url)
