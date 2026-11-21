"""Import a single UK Adzuna search profile into the inbox, on demand."""

import asyncio
import os
import sys

import httpx2
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from funnel.modules.discovery.models import JobBoardRow
from funnel.modules.discovery.service import build_search_profile_service
from funnel.modules.inbox.feeds import read_adzuna
from funnel.modules.inbox.repository import FeedImportRepository
from funnel.modules.inbox.service import offer_row


async def main() -> int:
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        print("Set ADZUNA_APP_ID and ADZUNA_APP_KEY in .env before importing.")
        return 1
    engine = create_async_engine(os.environ["DATABASE_URL"])
    try:
        async with async_sessionmaker(engine).begin() as session:
            profiles = await build_search_profile_service(session).all_terms()
            name = os.environ.get("ADZUNA_PROFILE", "").strip()
            profile = next(
                (p for p in profiles if not name or p.name.casefold() == name.casefold()), None
            )
            if profile is None:
                print("No matching search profile. Check ADZUNA_PROFILE or create a profile.")
                return 1
            board = await session.scalar(
                select(JobBoardRow).where(func.lower(JobBoardRow.name) == "adzuna")
            )
            if board is None:
                print("Adzuna is missing from Sources. Run just seed-job-boards first.")
                return 1
            async with httpx2.AsyncClient(
                timeout=20, params={"app_id": app_id, "app_key": app_key}
            ) as client:
                try:
                    offers = await read_adzuna(client, profile.titles, profile.location)
                except httpx2.HTTPStatusError as error:
                    print(f"Adzuna returned HTTP {error.response.status_code}.")
                    return 1
                except httpx2.HTTPError, ValueError, TypeError, AttributeError, KeyError:
                    # Never print request URLs: the provider requires credentials in the query.
                    print("Could not read Adzuna search results.")
                    return 1
            repository = FeedImportRepository(session)
            added = await repository.add_new([offer_row(o, job_board_id=board.id) for o in offers])
            filtered = await repository.count_filtered(added, profiles)
            print(f"{profile.name}: {len(offers)} found, {len(added)} new, {filtered} filtered.")
            return 0
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
