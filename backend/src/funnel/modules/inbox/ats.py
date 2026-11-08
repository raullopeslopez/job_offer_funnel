"""One adapter per ATS: read a company's public job board and turn each job into a FeedOffer.

Response shapes checked against the live APIs on 2026-11-08. An unknown board answers 404.
"""

from collections.abc import Awaitable, Callable, Mapping
from html import unescape
from typing import Any, Final

import httpx2

from funnel.modules.inbox.domain import Ats, FeedOffer

Reader = Callable[[httpx2.AsyncClient, str], Awaitable[list[Mapping[str, Any]]]]
# Where each ATS puts the title, description and link of a job.
Fields = tuple[str, str, str]

# Offers are stored in VARCHAR(200) columns.
_MAX_TEXT = 200


async def _get_json(client: httpx2.AsyncClient, url: str) -> Any:
    response = await client.get(url)
    response.raise_for_status()
    return response.json()


async def _greenhouse(client: httpx2.AsyncClient, board: str) -> list[Mapping[str, Any]]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
    jobs: list[Mapping[str, Any]] = (await _get_json(client, url))["jobs"]
    # The description comes as escaped HTML: unescaped, its words can be matched.
    return [{**job, "content": unescape(job.get("content") or "")} for job in jobs]


async def _lever(client: httpx2.AsyncClient, board: str) -> list[Mapping[str, Any]]:
    jobs: list[Mapping[str, Any]] = await _get_json(
        client, f"https://api.lever.co/v0/postings/{board}?mode=json"
    )
    return jobs


async def _ashby(client: httpx2.AsyncClient, board: str) -> list[Mapping[str, Any]]:
    body = await _get_json(client, f"https://api.ashbyhq.com/posting-api/job-board/{board}")
    return [job for job in body["jobs"] if job.get("isListed", True)]


ADAPTERS: Final[Mapping[Ats, tuple[Reader, Fields]]] = {
    Ats.ASHBY: (_ashby, ("title", "descriptionPlain", "jobUrl")),
    Ats.GREENHOUSE: (_greenhouse, ("title", "content", "absolute_url")),
    Ats.LEVER: (_lever, ("text", "descriptionPlain", "hostedUrl")),
}


def _offer(job: Mapping[str, Any], fields: Fields, company: str) -> FeedOffer | None:
    """None when the job lacks a title or a link."""
    title, description, url = (job.get(name) for name in fields)
    if not (isinstance(title, str) and title.strip() and isinstance(url, str) and url.strip()):
        return None
    return FeedOffer(
        title=title.strip()[:_MAX_TEXT],
        company=company,
        description=description if isinstance(description, str) else "",
        url=url.strip(),
    )


class BoardReader:
    """Reads any ATS board with one HTTP client; the offers are for the watched company."""

    def __init__(self, client: httpx2.AsyncClient) -> None:
        self._client = client

    async def read(self, ats: Ats, board: str, company: str) -> list[FeedOffer]:
        reader, fields = ADAPTERS[ats]
        offers = [_offer(job, fields, company) for job in await reader(self._client, board)]
        return [offer for offer in offers if offer is not None]
