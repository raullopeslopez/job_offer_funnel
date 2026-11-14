"""Read the offers of a job alert email: one reader per board, chosen by the sender.

Format checked against real LinkedIn job alerts on 2026-11-11. The plain-text body is
the alert's heading, then one block per offer (title, company, location, maybe a few
extra lines and the posting's link) separated by lines of dashes. Only the link is
looked for, so the language of the email does not matter.
"""

import re
from collections.abc import Callable, Mapping
from typing import Final

from funnel.modules.discovery.domain import EmailAlert
from funnel.modules.inbox.domain import FeedOffer, UnsupportedAlertError, published_location

# Offers are stored in VARCHAR(200) columns.
_MAX_TEXT = 200
_SEPARATOR = re.compile(r"^-{10,}\s*$", re.MULTILINE)
_LINKEDIN_JOB = re.compile(r"https://www\.linkedin\.com/comm/jobs/view/(\d+)")


def _linkedin(text: str) -> list[FeedOffer]:
    _heading, _, body = text.strip().partition("\n")
    offers = []
    for block in _SEPARATOR.split(body):
        link = _LINKEDIN_JOB.search(block)
        lines = [line.strip() for line in block[: link.start()].splitlines()] if link else []
        title, company, location, *_ = [line for line in lines if line] + ["", "", ""]
        if link and title and company:
            offers.append(
                FeedOffer(
                    title=title[:_MAX_TEXT],
                    company=company[:_MAX_TEXT],
                    description="",
                    # Without the email's tracking parameters.
                    url=f"https://www.linkedin.com/jobs/view/{link.group(1)}/",
                    location=published_location(location),
                )
            )
    return offers


READERS: Final[Mapping[str, tuple[EmailAlert, Callable[[str], list[FeedOffer]]]]] = {
    "jobalerts-noreply@linkedin.com": (EmailAlert.LINKEDIN, _linkedin),
}


def read_alert(sender: str, text: str) -> tuple[EmailAlert, list[FeedOffer]]:
    """The alert the email comes from and its offers; rejects any other email."""
    try:
        alert, reader = READERS[sender.casefold()]
    except KeyError as error:
        raise UnsupportedAlertError(f"Emails from {sender} are not a supported alert") from error
    return alert, reader(text)
