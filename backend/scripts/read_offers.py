"""Have the offer reader read every offer left to read, through the API, until none is left.

Made for `just read-prod`: the API of `just dev-prod`, which reads with Claude Code on the
user's subscription (specs/inbox/offer_readings.feature), so there is no per-minute quota
to wait for. The API comes from API_URL (default: the one of `just dev-prod`) and the token
from AUTH_TOKEN, which is never printed. It stops when nothing is left, or when a call
reads nothing (the reader failed on every offer of it); the deployed app keeps reading
with Groq every 6 hours.
"""

import os
import sys
from http import HTTPStatus
from urllib.error import HTTPError, URLError

from import_offers import call


def main() -> int:
    api = f"{os.environ.get('API_URL', 'http://localhost:8000')}/api/v1"
    while True:
        try:
            batch = call("POST", f"{api}/offers/readings")
        except HTTPError as error:
            if error.code == HTTPStatus.SERVICE_UNAVAILABLE:
                print("The API has no offer reader: is `claude` installed?")
            else:
                print(f"FAILED    offer readings: {error.code} {error.read().decode()}")
            return 1
        except (URLError, TimeoutError) as error:
            print(f"FAILED    offer readings: {error} (is `just dev-prod` running?)")
            return 1
        print(
            f"read      {batch['read']} offers, failed on {batch['failed']}, {batch['left']} left",
            flush=True,
        )
        if batch["left"] == 0:
            return 0
        if batch["read"] == 0:
            return 1


if __name__ == "__main__":
    sys.exit(main())
