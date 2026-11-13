"""Import the offers of every imported job board, watched company and email alert through
the API.

Run every 6 hours by `.github/workflows/import-offers.yml` against Render, or by hand with
`just import-offers`. The API comes from API_URL (default: the one run by `just up`) and the
token from AUTH_TOKEN, which is never printed. A job board still in its cooldown (429) and a
feed or board that is not available (`feed-unavailable`, `board-unavailable`: outside services
we do not control) are skipped, not failures. Any other error makes the script exit with 1
after trying every source.

Email alerts are read by IMAP from the Gmail account dedicated to them (docs/fase1.md), with
GMAIL_ADDRESS and GMAIL_APP_PASSWORD (an app password, never printed); without them they are
skipped. Each alert the API takes gets the Gmail label `funnel-imported`, so it is sent only
once; whether it is read stays as is.

Last, the offer reader reads the new offers (specs/inbox/offer_readings.feature); an API
without one (no GROQ_API_KEY) skips it.
"""

import email
import imaplib
import json
import os
import sys
import time
from email import policy
from email.message import EmailMessage
from email.utils import parseaddr
from http import HTTPStatus
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Render's free plan sleeps the API: the first request can take a while to wake it up.
TIMEOUT_SECONDS = 120
WAKE_UP_ATTEMPTS = 3
# The API's largest page: more job boards than this would need paging.
PAGE_LIMIT = 100


# The offer reader's free plan counts tokens by the minute (modules/inbox/reader.py): one
# call a minute, for at most 8 minutes of the workflow's 15.
READING_PAUSE_SECONDS = 62
READING_ROUNDS = 8

# The API's problem types for a source that is down: a normal outcome, not a failure.
UNAVAILABLE_SOURCE_PROBLEMS = ("feed-unavailable", "board-unavailable")
# Imported when the script asks; `email` job boards are imported as their alerts arrive.
IMPORTED_ON_DEMAND = frozenset({"api", "rss"})
IMAP_HOST = "imap.gmail.com"
IMPORTED_LABEL = "funnel-imported"
# Gmail search syntax; the label keeps an alert from being sent twice.
ALERTS_QUERY = f"from:jobalerts-noreply@linkedin.com -label:{IMPORTED_LABEL} newer_than:14d"


def call(method: str, url: str, body: Any = None) -> Any:
    headers = {"Authorization": f"Bearer {os.environ['AUTH_TOKEN']}"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    request = Request(url, data=data, headers=headers, method=method)
    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.loads(response.read() or b"null")


def wake_up(api_url: str) -> None:
    for attempt in range(1, WAKE_UP_ATTEMPTS + 1):
        try:
            call("GET", f"{api_url}/health")
            return
        except (HTTPError, URLError, TimeoutError) as error:
            print(f"waking up the API (attempt {attempt}): {error}")
            if attempt == WAKE_UP_ATTEMPTS:
                raise
            time.sleep(10)


def import_from(label: str, url: str) -> bool:
    """Return whether the import worked or was skipped by the job board's cooldown."""
    try:
        result = call("POST", url)
    except HTTPError as error:
        if error.code == HTTPStatus.TOO_MANY_REQUESTS:
            print(f"skipped   {label} (imported less than 6 hours ago)")
            return True
        body = error.read().decode()
        if any(f"/problems/{slug}" in body for slug in UNAVAILABLE_SOURCE_PROBLEMS):
            print(f"skipped   {label} (source not available, retried in the next run): {body}")
            return True
        print(f"FAILED    {label}: {error.code} {body}")
        return False
    except (URLError, TimeoutError) as error:
        print(f"FAILED    {label}: {error}")
        return False
    print(
        f"imported  {label}: found {result['found']}, added {result['added']}"
        f" ({result['filtered']} filtered), expired {result['expired']}"
    )
    return True


def _all_mail(imap: imaplib.IMAP4_SSL) -> str:
    """Gmail's "All Mail" folder, whose name depends on the account's language."""
    _, folders = imap.list()
    for folder in folders:
        line = cast(bytes, folder).decode()
        if r"\All" in line:
            return line.rsplit(' "/" ', 1)[1]
    return "INBOX"


def _alert(imap: imaplib.IMAP4_SSL, uid: bytes) -> dict[str, str]:
    # BODY.PEEK leaves the email unread if it was.
    _, data = imap.uid("FETCH", uid, "(BODY.PEEK[])")
    message = cast(EmailMessage, email.message_from_bytes(data[0][1], policy=policy.default))
    body = message.get_body(preferencelist=("plain",))
    text = "" if body is None else cast(EmailMessage, body).get_content()
    return {"sender": parseaddr(str(message["From"]))[1], "text": text}


def _send_alert(api: str, uid: bytes, alert: dict[str, str]) -> bool:
    try:
        result = call("POST", f"{api}/email-alerts/imports", alert)
    except HTTPError as error:
        print(f"FAILED    alert {uid.decode()}: {error.code} {error.read().decode()}")
        return False
    except (URLError, TimeoutError) as error:
        print(f"FAILED    alert {uid.decode()}: {error}")
        return False
    print(
        f"imported  alert {uid.decode()}: found {result['found']},"
        f" added {result['added']} ({result['filtered']} filtered)"
    )
    return True


def import_alerts(api: str) -> bool:
    """Send every new LinkedIn job alert to the API; return whether all of them worked."""
    address, password = os.environ.get("GMAIL_ADDRESS"), os.environ.get("GMAIL_APP_PASSWORD")
    if not (address and password):
        print("skipped   email alerts (GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set)")
        return True
    results = []
    with imaplib.IMAP4_SSL(IMAP_HOST) as imap:
        imap.login(address, password)
        imap.select(_all_mail(imap))
        _, found = imap.uid("SEARCH", "X-GM-RAW", f'"{ALERTS_QUERY}"')
        for uid in found[0].split():
            sent = _send_alert(api, uid, _alert(imap, uid))
            if sent:
                imap.uid("STORE", uid, "+X-GM-LABELS", IMPORTED_LABEL)
            results.append(sent)
    return all(results)


def read_offers(api: str) -> bool:
    """Have the offer reader read the new offers, a few a minute; return whether it worked.

    The API reads up to 5 per call and the reader's plan allows about that many a minute, so
    the script waits between calls and stops after READING_ROUNDS. A round that reads
    nothing means the reader's quota is spent: what is left waits for the next run.
    """
    for _round in range(READING_ROUNDS):
        try:
            batch = call("POST", f"{api}/offers/readings")
        except HTTPError as error:
            if error.code == HTTPStatus.SERVICE_UNAVAILABLE:
                print("skipped   offer readings (the API has no offer reader)")
                return True
            print(f"FAILED    offer readings: {error.code} {error.read().decode()}")
            return False
        except (URLError, TimeoutError) as error:
            print(f"FAILED    offer readings: {error}")
            return False
        print(
            f"read      {batch['read']} offers, failed on {batch['failed']}, {batch['left']} left"
        )
        if batch["left"] == 0 or batch["read"] == 0:
            break
        time.sleep(READING_PAUSE_SECONDS)
    return True


def main() -> int:
    api_url = os.environ.get("API_URL", f"http://localhost:{os.environ.get('API_PORT', '8080')}")
    api = f"{api_url}/api/v1"
    wake_up(api_url)
    results = [
        import_from(f"job board {board['name']}", f"{api}/job-boards/{board['id']}/imports")
        for board in call("GET", f"{api}/job-boards?limit={PAGE_LIMIT}")["items"]
        if board["import_method"] in IMPORTED_ON_DEMAND
    ]
    results += [
        import_from(
            f"company {company['name']}", f"{api}/watched-companies/{company['id']}/imports"
        )
        for company in call("GET", f"{api}/watched-companies")
    ]
    results.append(import_alerts(api))
    results.append(read_offers(api))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
