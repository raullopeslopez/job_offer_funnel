"""Stop hook: if backend/ has uncommitted changes, `just check` must pass before the turn ends.

Exit code 2 blocks the stop and shows stderr to Claude.
"""

import json
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
OUTPUT_TAIL_LINES = 40


def _backend_has_changes() -> bool:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", "backend"],
        cwd=PROJECT,
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(status.stdout.strip())


def main() -> int:
    payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    if payload.get("stop_hook_active") or not _backend_has_changes():
        return 0
    result = subprocess.run(
        ["just", "check"],
        cwd=PROJECT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode == 0:
        return 0
    output = (result.stdout + result.stderr).strip().splitlines()
    tail = "\n".join(output[-OUTPUT_TAIL_LINES:])
    print(
        f"`just check` failed with uncommitted backend changes. Fix it:\n{tail}",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
