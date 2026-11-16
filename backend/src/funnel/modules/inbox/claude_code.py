"""The `claude` CLI on the user's Claude subscription, which only runs where it is
installed and signed in: the offer reader and the offer triager ask it like they ask
Groq. It runs with no tools, no settings, no MCP servers and no saved session, from an
empty folder: it only sees what it is told."""

import asyncio
import json
import subprocess
import tempfile
from collections.abc import Sequence
from typing import Any, Final

# A batch of 20 takes Sonnet a minute or two.
TIMEOUT_SECONDS: Final = 600
# Not run, timed out, or not the JSON asked for.
FAILURES: Final = (
    OSError,
    subprocess.SubprocessError,
    ValueError,
    TypeError,
    AttributeError,
)


async def ask(  # noqa: PLR0913, PLR0917  # what the CLI is told, one argument each
    command: Sequence[str],
    model: str,
    instructions: str,
    schema: dict[str, Any],
    question: str,
) -> Any:  # noqa: ANN401  # the JSON the schema describes, checked by the caller
    """What Claude answers to the question, as the JSON the schema describes.

    Raises one of FAILURES when the CLI cannot run, times out or fails.
    """
    arguments = [
        *command,
        "-p",
        "--model",
        model,
        "--output-format",
        "json",
        "--system-prompt",
        instructions,
        "--json-schema",
        json.dumps(schema),
        "--tools",
        "",
        "--setting-sources",
        "",
        "--strict-mcp-config",
        "--no-session-persistence",
    ]
    # A thread, not an asyncio subprocess: those need the proactor loop on Windows.
    done = await asyncio.to_thread(_run, arguments, question)
    result = json.loads(done.stdout)
    if done.returncode != 0 or result.get("is_error"):
        raise ValueError(f"claude failed ({done.returncode}): {done.stdout[:500]}")
    return result.get("structured_output")


def _run(arguments: list[str], question: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as empty:
        return subprocess.run(  # noqa: S603  # our own arguments, never the user's
            arguments,
            input=question,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=TIMEOUT_SECONDS,
            check=False,
            cwd=empty,
        )
