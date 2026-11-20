import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.integration


async def _setting(session_factory: async_sessionmaker[AsyncSession], name: str) -> str:
    async with session_factory() as session:
        return str(await session.scalar(text(f"SHOW {name}")))


def test_request_sessions_run_without_jit(client: TestClient) -> None:
    # Arrange
    session_factory = client.app.state.session_factory  # type: ignore[attr-defined]

    # Act
    jit = client.portal.call(_setting, session_factory, "jit")  # type: ignore[union-attr]

    # Assert
    assert jit == "off"
