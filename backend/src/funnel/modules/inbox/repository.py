from sqlalchemy.ext.asyncio import AsyncSession


class OfferRepository:
    """Never commits: the request session does."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
