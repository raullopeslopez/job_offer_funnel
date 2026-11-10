"""Import the offers of every public feed and watched company through the API.

Run every 6 hours by `.github/workflows/import-offers.yml` against Render, or by hand with
`just import-offers`. The API comes from API_URL (default: the one run by `just up`) and the
token from AUTH_TOKEN, which is never printed. A feed still in its cooldown (429) is skipped,
not a failure. Any other error makes the script exit with 1 after trying every source.
"""

import json
import os
import sys
import time
from http import HTTPStatus
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Render's free plan sleeps the API: the first request can take a while to wake it up.
TIMEOUT_SECONDS = 120
WAKE_UP_ATTEMPTS = 3


def call(method: str, url: str) -> Any:
    headers = {"Authorization": f"Bearer {os.environ['AUTH_TOKEN']}"}
    with urlopen(Request(url, headers=headers, method=method), timeout=TIMEOUT_SECONDS) as response:
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
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
