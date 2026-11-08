"""PostToolUse hook: run `ruff format` on an edited backend Python file.

Only formatting: `ruff check --fix` here would delete imports added in one edit
and used in the next. Linting runs at the end of the turn (check_on_stop.py).
"""

import json
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "backend"


def main() -> None:
    payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    file_path = payload.get("tool_input", {}).get("file_path", "")
    path = Path(file_path).resolve() if file_path else None
    if path is None or path.suffix != ".py" or BACKEND not in path.parents:
        return
    subprocess.run(
        ["uv", "run", "--project", str(BACKEND), "ruff", "format", str(path)],
        capture_output=True,
        check=False,
    )


if __name__ == "__main__":
    main()
