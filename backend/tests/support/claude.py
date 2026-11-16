"""A stand-in for the `claude` CLI: tests never run the real one."""

import json
import sys
from pathlib import Path
from typing import Any

# Writes what it was asked next to itself and prints the result the test gives it, with
# its exit code.
_FAKE_CLAUDE = """\
import json, os, sys
here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "asked.json"), "w", encoding="utf-8") as asked:
    json.dump({"args": sys.argv[1:], "stdin": sys.stdin.read(), "cwd": os.getcwd()}, asked)
with open(os.path.join(here, "result.json"), encoding="utf-8") as result:
    told = json.load(result)
sys.stdout.write(told["stdout"])
sys.exit(told["code"])
"""


def fake_claude(folder: Path, stdout: str, code: int = 0) -> list[str]:
    """The command of a `claude` that answers `stdout` with exit code `code`."""
    script = folder / "claude.py"
    script.write_text(_FAKE_CLAUDE, encoding="utf-8")
    (folder / "result.json").write_text(json.dumps({"stdout": stdout, "code": code}))
    return [sys.executable, str(script)]


def asked(folder: Path) -> dict[str, Any]:
    """What the fake `claude` in `folder` was asked: its arguments, input and folder."""
    told: dict[str, Any] = json.loads((folder / "asked.json").read_text(encoding="utf-8"))
    return told


def result(structured: Any, *, is_error: bool = False) -> str:  # noqa: ANN401  # any JSON
    """The output of `claude -p --output-format json` with that structured output."""
    return json.dumps({"type": "result", "is_error": is_error, "structured_output": structured})
