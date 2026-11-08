"""Register the job boards of a JSON file in the API run by `just up`.

Safe to run again: job boards that already exist are skipped. The token comes from the
AUTH_TOKEN environment variable (`just` loads it from .env) and is never printed.
"""

import json
import os
import sys
from http import HTTPStatus
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main(seed_file: Path) -> int:
    url = f"http://localhost:{os.environ.get('API_PORT', '8080')}/api/v1/job-boards"
    headers = {
        "Authorization": f"Bearer {os.environ['AUTH_TOKEN']}",
        "Content-Type": "application/json",
    }
    failures = 0
    for job_board in json.loads(seed_file.read_text(encoding="utf-8")):
        request = Request(url, json.dumps(job_board).encode(), headers, method="POST")
        try:
            with urlopen(request) as response:
                print(f"created   {job_board['name']} ({response.status})")
        except HTTPError as error:
            if error.code == HTTPStatus.CONFLICT:
                print(f"skipped   {job_board['name']} (already exists)")
            else:
                failures += 1
                print(f"FAILED    {job_board['name']}: {error.code} {error.read().decode()}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
