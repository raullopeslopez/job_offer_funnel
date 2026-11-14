"""One adapter per public feed: read its JSON API and turn each job into a FeedOffer.
Plus one reader for every RSS, whose items read "Company: Title" (Evenbreak's convention).

Response shapes checked against the live APIs on 2026-11-08 (Jobicy's pages on 2026-11-12,
the locations on 2026-11-14) and the RSS on 2026-11-11; terms in docs/fase0.md.
"""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any, Final
from urllib.parse import quote
from xml.etree import ElementTree

import httpx2

from funnel.modules.discovery.domain import QUERY_PLACEHOLDER, Feed
from funnel.modules.inbox.domain import FeedOffer, published_location

# Titles to search by, for the feeds whose terms rule out reading them whole.
Reader = Callable[[httpx2.AsyncClient, Sequence[str]], Awaitable[list[FeedOffer]]]

# Offers are stored in VARCHAR(200) columns.
_MAX_TEXT = 200
# Jobicy publishes about 14 offers an hour, newest first, 100 a page at most: 3 pages
# cover the hours between two imports with room to spare.
_JOBICY_PAGE_SIZE = 100
_JOBICY_PAGES = 3


async def _get_json(
    client: httpx2.AsyncClient, url: str, params: Mapping[str, str] | None = None
) -> Any:
    response = await client.get(url, params=params)
    response.raise_for_status()
    return response.json()


# Where each feed puts the title, company, description, link and location of a job.
Fields = tuple[str, str, str, str, str]


def _offer(job: Mapping[str, Any], fields: Fields) -> FeedOffer | None:
    """None when the job lacks what an offer needs."""
    title, company, description, url, location = (job.get(name) for name in fields)
    if not (isinstance(title, str) and isinstance(company, str) and isinstance(url, str)):
        return None
    if not (title.strip() and company.strip() and url.strip()):
        return None
    return FeedOffer(
        title=title.strip()[:_MAX_TEXT],
        company=company.strip()[:_MAX_TEXT],
        description=description if isinstance(description, str) else "",
        url=url.strip(),
        location=published_location(location),
    )


def _kept(offers: Sequence[FeedOffer | None]) -> list[FeedOffer]:
    return [offer for offer in offers if offer is not None]


async def _remoteok(client: httpx2.AsyncClient, _titles: Sequence[str]) -> list[FeedOffer]:
    jobs = await _get_json(client, "https://remoteok.com/api")
    # The first element is the legal notice, not a job.
    return _kept(
        [
            _offer(job, ("position", "company", "description", "url", "location"))
            for job in jobs
            if "position" in job
        ]
    )


async def _remotive(client: httpx2.AsyncClient, _titles: Sequence[str]) -> list[FeedOffer]:
    body = await _get_json(client, "https://remotive.com/api/remote-jobs")
    return _kept(
        [
            _offer(
                job, ("title", "company_name", "description", "url", "candidate_required_location")
            )
            for job in body["jobs"]
        ]
    )


async def _himalayas(client: httpx2.AsyncClient, titles: Sequence[str]) -> list[FeedOffer]:
    # Its terms rule out bulk collection: search by each title instead of reading it all.
    # Applying must go through applicationLink, so that is the link kept.
    offers: dict[str, FeedOffer] = {}
    for title in titles:
        body = await _get_json(client, "https://himalayas.app/jobs/api/search", {"q": title})
        for job in body["jobs"]:
            offer = _offer(
                job,
                ("title", "companyName", "description", "applicationLink", "locationRestrictions"),
            )
            if offer is not None:
                offers.setdefault(offer.url, offer)
    return list(offers.values())


async def _jobicy(client: httpx2.AsyncClient, _titles: Sequence[str]) -> list[FeedOffer]:
    offers: list[FeedOffer | None] = []
    params = {"count": str(_JOBICY_PAGE_SIZE)}
    for _page in range(_JOBICY_PAGES):
        body = await _get_json(client, "https://jobicy.com/api/v2/remote-jobs", params)
        offers += [
            _offer(job, ("jobTitle", "companyName", "jobDescription", "url", "jobGeo"))
            for job in body["jobs"]
        ]
        # The cursor of the next page; none on the last one.
        cursor = body.get("nextCursor")
        if not isinstance(cursor, str):
            break
        params = params | {"cursor": cursor}
    return _kept(offers)


READERS: Final[Mapping[Feed, Reader]] = {
    Feed.HIMALAYAS: _himalayas,
    Feed.JOBICY: _jobicy,
    Feed.REMOTEOK: _remoteok,
    Feed.REMOTIVE: _remotive,
}


# The RSS publishes no location.
_RSS_FIELDS: Final = ("title", "company", "description", "url", "location")


def _rss_offer(item: ElementTree.Element) -> FeedOffer | None:
    """None when the item lacks a company, a title or a link."""
    company, colon, title = (item.findtext("title") or "").partition(":")
    if not colon:
        return None
    job = {
        "title": title,
        "company": company,
        "description": item.findtext("description") or "",
        "url": item.findtext("link") or "",
    }
    return _offer(job, _RSS_FIELDS)


def _rss_offers(document: str) -> list[FeedOffer]:
    try:
        # Safe on untrusted input: expat resolves no external entities and caps expansion.
        root = ElementTree.fromstring(document)
    except ElementTree.ParseError as error:
        msg = "not XML"
        raise ValueError(msg) from error
    channel = root.find("channel")
    if root.tag != "rss" or channel is None:
        msg = "not an RSS"
        raise ValueError(msg)
    return _kept([_rss_offer(item) for item in channel.iter("item")])


async def _rss(
    client: httpx2.AsyncClient, url_template: str, titles: Sequence[str]
) -> list[FeedOffer]:
    # Read once per title; an item found by several titles is one offer.
    offers: dict[str, FeedOffer] = {}
    for title in titles:
        url = url_template.replace(f"{{{QUERY_PLACEHOLDER}}}", quote(title, safe=""))
        response = await client.get(url)
        response.raise_for_status()
        for offer in _rss_offers(response.text):
            offers.setdefault(offer.url, offer)
    return list(offers.values())


class FeedReader:
    """Reads any feed or RSS with one HTTP client; each feed's adapter knows its JSON."""

    def __init__(self, client: httpx2.AsyncClient) -> None:
        self._client = client

    async def read(self, feed: Feed, titles: Sequence[str]) -> list[FeedOffer]:
        return await READERS[feed](self._client, titles)

    async def read_rss(self, url_template: str, titles: Sequence[str]) -> list[FeedOffer]:
        return await _rss(self._client, url_template, titles)
