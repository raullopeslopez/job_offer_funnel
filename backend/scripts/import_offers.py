"""Import the offers of every public feed, watched company and email alert through the API.

Run every 6 hours by `.github/workflows/import-offers.yml` against Render, or by hand with
`just import-offers`. The API comes from API_URL (default: the one run by `just up`) and the
token from AUTH_TOKEN, which is never printed. A feed still in its cooldown (429) is skipped,
not a failure. Any other error makes the script exit with 1 after trying every source.

Email alerts are read from Gmail by IMAP with GMAIL_ADDRESS and GMAIL_APP_PASSWORD (an app
password, never printed); without them they are skipped. Each alert sent to the API gets
the Gmail label `funnel-imported`, so it is sent only once; whether it is read stays as is.
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
    """Return whether the import worked or was skipped by the feed's cooldown."""
    try:
        result = call("POST", url)
    except HTTPError as error:
        if error.code == HTTPStatus.TOO_MANY_REQUESTS:
            print(f"skipped   {label} (imported less than 6 hours ago)")
            return True
        print(f"FAILED    {label}: {error.code} {error.read().decode()}")
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


def _alert(imap: imaplib.IMAP4_SSL, uid: bytes) -> tuple[str, str]:
    # BODY.PEEK leaves the email unread if it was.
    _, data = imap.uid("FETCH", uid, "(BODY.PEEK[])")
    message = cast(EmailMessage, email.message_from_bytes(data[0][1], policy=policy.default))
    body = message.get_body(preferencelist=("plain",))
    text = "" if body is None else cast(EmailMessage, body).get_content()
    return parseaddr(str(message["From"]))[1], text


def import_alerts(api: str) -> bool:
    """Send every new LinkedIn job alert to the API; return whether all of them worked."""
    address, password = os.environ.get("GMAIL_ADDRESS"), os.environ.get("GMAIL_APP_PASSWORD")
    if not (address and password):
        print("skipped   email alerts (GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set)")
        return True
    worked = True
    with imaplib.IMAP4_SSL(IMAP_HOST) as imap:
        imap.login(address, password)
        imap.select(_all_mail(imap))
        _, found = imap.uid("SEARCH", "X-GM-RAW", f'"{ALERTS_QUERY}"')
        for uid in found[0].split():
            sender, text = _alert(imap, uid)
            try:
                body = {"sender": sender, "text": text}
                result = call("POST", f"{api}/email-alerts/imports", body)
            except HTTPError as error:
                print(f"FAILED    alert {uid.decode()}: {error.code} {error.read().decode()}")
                worked = False
                continue
            except (URLError, TimeoutError) as error:
                print(f"FAILED    alert {uid.decode()}: {error}")
                worked = False
                continue
            imap.uid("STORE", uid, "+X-GM-LABELS", IMPORTED_LABEL)
            print(
                f"imported  alert {result['alert']}: found {result['found']},"
                f" added {result['added']} ({result['filtered']} filtered)"
            )
    return worked


def main() -> int:
    api_url = os.environ.get("API_URL", f"http://localhost:{os.environ.get('API_PORT', '8080')}")
    api = f"{api_url}/api/v1"
    wake_up(api_url)
    results = [
        import_from(f"feed {feed['feed']}", f"{api}/feeds/{feed['feed']}/imports")
        for feed in call("GET", f"{api}/feeds")
    ]
    results += [
        import_from(
            f"company {company['name']}", f"{api}/watched-companies/{company['id']}/imports"
        )
        for company in call("GET", f"{api}/watched-companies")
    ]
    results.append(import_alerts(api))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
