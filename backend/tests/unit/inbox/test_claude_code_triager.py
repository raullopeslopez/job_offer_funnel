import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import httpx2
import pytest
from pydantic import SecretStr

from funnel.core.config import Settings
from funnel.modules.inbox.domain import OfferText, OfferTriagerError, TriageContext, TriageReply
from funnel.modules.inbox.router import offer_triager
from funnel.modules.inbox.triager import ClaudeCodeTriager, OfferTriager

pytestmark = pytest.mark.unit

OFFERS = [OfferText("Backend Engineer", "Acme", "Python services.")]
CONTEXT = TriageContext(profiles=[], decisions=[], mistakes=[])
ANSWER = {
    "offers": [
        {
            "offer": 0,
            "verdict": "ok",
            "why_yes": "A Python backend.",
            "quote_yes": "Python services",
            "why_not": None,
            "quote_not": None,
            "confidence": "high",
            "reason": None,
            "evidence": None,
        }
    ],
    "exclusions": [],
}
# A stand-in for the `claude` CLI: writes what it was asked next to itself and prints
# the result the test gives it, with its exit code.
FAKE_CLAUDE = """\
import json, os, sys
here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "asked.json"), "w", encoding="utf-8") as asked:
    json.dump({"args": sys.argv[1:], "stdin": sys.stdin.read(), "cwd": os.getcwd()}, asked)
with open(os.path.join(here, "result.json"), encoding="utf-8") as result:
    told = json.load(result)
sys.stdout.write(told["stdout"])
sys.exit(told["code"])
"""


def _triage(tmp_path: Path, stdout: str, code: int = 0) -> TriageReply:
    script = tmp_path / "claude.py"
    script.write_text(FAKE_CLAUDE, encoding="utf-8")
    (tmp_path / "result.json").write_text(json.dumps({"stdout": stdout, "code": code}))
    triager = ClaudeCodeTriager([sys.executable, str(script)], "sonnet")
    return asyncio.run(triager.triage(OFFERS, CONTEXT))


def _result(structured: Any, *, is_error: bool = False) -> str:
    return json.dumps({"type": "result", "is_error": is_error, "structured_output": structured})


def _asked(tmp_path: Path) -> dict[str, Any]:
    asked: dict[str, Any] = json.loads((tmp_path / "asked.json").read_text(encoding="utf-8"))
    return asked


def test_reads_what_claude_answers_for_each_offer(tmp_path: Path) -> None:
    # Act
    reply = _triage(tmp_path, _result(ANSWER))

    # Assert
    assert reply.answers[0].verdict == "ok"
    assert reply.answers[0].quote_yes == "Python services"


def test_asks_claude_with_no_tools_settings_or_session_from_a_throwaway_folder(
    tmp_path: Path,
) -> None:
    # Act
    _triage(tmp_path, _result(ANSWER))

    # Assert
    asked = _asked(tmp_path)
    args = asked["args"]
    assert args[args.index("--model") + 1] == "sonnet"
    assert args[args.index("--tools") + 1] == ""
    assert args[args.index("--setting-sources") + 1] == ""
    assert {"-p", "--strict-mcp-config", "--no-session-persistence"} <= set(args)
    assert "--json-schema" in args
    assert "Python services." in asked["stdin"]
    assert Path(asked["cwd"]) != Path.cwd()
    assert not Path(asked["cwd"]).exists()  # a throwaway folder, removed afterwards


@pytest.mark.parametrize(
    ("stdout", "code"),
    [
        pytest.param(_result(ANSWER), 1, id="exit code"),
        pytest.param(_result(None, is_error=True), 0, id="error result"),
        pytest.param("not json", 0, id="not json"),
        pytest.param(_result({"verdict": "ok"}), 0, id="not the schema"),
        pytest.param("[]", 0, id="not an object"),
    ],
)
def test_a_failed_answer_is_a_triager_error(tmp_path: Path, stdout: str, code: int) -> None:
    # Act / Assert
    with pytest.raises(OfferTriagerError):
        _triage(tmp_path, stdout, code)


def test_a_missing_command_is_a_triager_error(tmp_path: Path) -> None:
    # Arrange
    triager = ClaudeCodeTriager([str(tmp_path / "no-such-claude")], "sonnet")

    # Act / Assert
    with pytest.raises(OfferTriagerError):
        asyncio.run(triager.triage(OFFERS, CONTEXT))


@pytest.mark.parametrize(
    ("triager", "groq_key", "claude", "expected"),
    [
        pytest.param("groq", "key", None, OfferTriager, id="Groq"),
        pytest.param("groq", "", "/bin/claude", None, id="Groq without its key"),
        pytest.param("claude-code", "", "/bin/claude", ClaudeCodeTriager, id="Claude Code"),
        pytest.param("claude-code", "key", None, None, id="Claude Code, not installed"),
    ],
)
def test_the_configured_triager_runs_only_when_it_can(  # noqa: PLR0913, PLR0917  # the cases
    monkeypatch: pytest.MonkeyPatch,
    triager: str,
    groq_key: str,
    claude: str | None,
    expected: type | None,
) -> None:
    # Arrange
    monkeypatch.setattr("funnel.modules.inbox.router.shutil.which", lambda _name: claude)
    settings = Settings(
        database_url="postgresql+asyncpg://unused",
        auth_token=SecretStr("unused"),
        groq_api_key=SecretStr(groq_key),
        offer_triager=triager,  # type: ignore[arg-type]  # the cases name valid ones
    )

    # Act
    chosen = offer_triager(settings, httpx2.AsyncClient())

    # Assert
    assert (type(chosen) if chosen else None) is expected
