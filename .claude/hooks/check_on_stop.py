"""Stop hook: the checks of each area with uncommitted changes must pass before the turn ends.

backend/ runs `just check`; frontend/ runs `just fe-check`.

Exit code 2 blocks the stop and shows stderr to Claude.
"""

import json
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
OUTPUT_TAIL_LINES = 40
CHECKS = {"backend": "check", "frontend": "fe-check"}


def _has_changes(area: str) -> bool:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", area],
        cwd=PROJECT,
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(status.stdout.strip())


def _run(recipe: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["just", recipe],
        cwd=PROJECT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def main() -> int:
    payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    if payload.get("stop_hook_active"):
        return 0
    for area, recipe in CHECKS.items():
        if not _has_changes(area):
            continue
        result = _run(recipe)
        if result.returncode == 0:
            continue
        output = (result.stdout + result.stderr).strip().splitlines()
        tail = "\n".join(output[-OUTPUT_TAIL_LINES:])
        print(
            f"`just {recipe}` failed with uncommitted {area} changes. Fix it:\n{tail}",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
