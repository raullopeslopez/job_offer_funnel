"""One adapter per public feed: read its JSON API and turn each job into a FeedOffer.

Response shapes checked against the live APIs on 2026-11-08; terms in docs/fase0.md.
"""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any, Final

import httpx2

from funnel.modules.discovery.domain import Feed
from funnel.modules.inbox.domain import FeedOffer

# Titles to search by, for the feeds whose terms rule out reading them whole.
Reader = Callable[[httpx2.AsyncClient, Sequence[str]], Awaitable[list[FeedOffer]]]

# Offers are stored in VARCHAR(200) columns.
_MAX_TEXT = 200
_JOBICY_PAGE_SIZE = 50


async def _get_json(
    client: httpx2.AsyncClient, url: str, params: Mapping[str, str] | None = None
) -> Any:
    response = await client.get(url, params=params)
    response.raise_for_status()
    return response.json()


# Where each feed puts the title, company, description and link of a job.
Fields = tuple[str, str, str, str]


def _offer(job: Mapping[str, Any], fields: Fields) -> FeedOffer | None:
    """None when the job lacks what an offer needs."""
    title, company, description, url = (job.get(name) for name in fields)
    if not (isinstance(title, str) and isinstance(company, str) and isinstance(url, str)):
        return None
    if not (title.strip() and company.strip() and url.strip()):
        return None
    return FeedOffer(
        title=title.strip()[:_MAX_TEXT],
        company=company.strip()[:_MAX_TEXT],
        description=description if isinstance(description, str) else "",
        url=url.strip(),
    )


def _kept(offers: Sequence[FeedOffer | None]) -> list[FeedOffer]:
    return [offer for offer in offers if offer is not None]


async def _remoteok(client: httpx2.AsyncClient, _titles: Sequence[str]) -> list[FeedOffer]:
    jobs = await _get_json(client, "https://remoteok.com/api")
    # The first element is the legal notice, not a job.
    return _kept(
        [
            _offer(job, ("position", "company", "description", "url"))
            for job in jobs
            if "position" in job
        ]
    )


async def _remotive(client: httpx2.AsyncClient, _titles: Sequence[str]) -> list[FeedOffer]:
    body = await _get_json(client, "https://remotive.com/api/remote-jobs")
    return _kept(
        [_offer(job, ("title", "company_name", "description", "url")) for job in body["jobs"]]
    )


async def _himalayas(client: httpx2.AsyncClient, titles: Sequence[str]) -> list[FeedOffer]:
    # Its terms rule out bulk collection: search by each title instead of reading it all.
    # Applying must go through applicationLink, so that is the link kept.
    offers: dict[str, FeedOffer] = {}
    for title in titles:
        body = await _get_json(client, "https://himalayas.app/jobs/api/search", {"q": title})
        for job in body["jobs"]:
            offer = _offer(job, ("title", "companyName", "description", "applicationLink"))
            if offer is not None:
                offers.setdefault(offer.url, offer)
    return list(offers.values())


async def _jobicy(client: httpx2.AsyncClient, _titles: Sequence[str]) -> list[FeedOffer]:
    body = await _get_json(
        client, "https://jobicy.com/api/v2/remote-jobs", {"count": str(_JOBICY_PAGE_SIZE)}
    )
    return _kept(
        [_offer(job, ("jobTitle", "companyName", "jobDescription", "url")) for job in body["jobs"]]
    )


READERS: Final[Mapping[Feed, Reader]] = {
    Feed.HIMALAYAS: _himalayas,
    Feed.JOBICY: _jobicy,
    Feed.REMOTEOK: _remoteok,
    Feed.REMOTIVE: _remotive,
}


class FeedReader:
    """Reads any feed with one HTTP client; each feed's adapter knows its JSON."""

    def __init__(self, client: httpx2.AsyncClient) -> None:
        self._client = client

    async def read(self, feed: Feed, titles: Sequence[str]) -> list[FeedOffer]:
        return await READERS[feed](self._client, titles)
