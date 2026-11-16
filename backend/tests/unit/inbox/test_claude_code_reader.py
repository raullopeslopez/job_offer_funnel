import asyncio
from pathlib import Path
from typing import Any

import httpx2
import pytest
from pydantic import SecretStr
from support.claude import asked, fake_claude, result

from funnel.core.config import Settings
from funnel.modules.discovery.domain import WorkMode
from funnel.modules.inbox.domain import OfferReaderError, OfferText, Reading
from funnel.modules.inbox.reader import ClaudeCodeReader, OfferReader, Question
from funnel.modules.inbox.router import offer_reader

pytestmark = pytest.mark.unit

QUESTIONS: list[Question] = [
    (OfferText("Backend Engineer", "Acme", "Fully remote. Hiring across Europe."), "Spain"),
    (OfferText("Data Engineer", "Globex", "Fully remote. Full-time."), None),
]


def _answer(offer: int, **answers: Any) -> dict[str, Any]:  # noqa: ANN401  # JSON values
    empty = {
        "work_mode": None,
        "work_mode_evidence": None,
        "admits_location": None,
        "admits_location_evidence": None,
        "stable": None,
        "stable_evidence": None,
    }
    return {"offer": offer, **empty, **answers}


def _read(tmp_path: Path, stdout: str, code: int = 0) -> list[Reading | OfferReaderError]:
    reader = ClaudeCodeReader(fake_claude(tmp_path, stdout, code), "sonnet")
    return asyncio.run(reader.read_batch(QUESTIONS))


def test_reads_what_claude_answers_for_each_offer_by_its_number(tmp_path: Path) -> None:
    # Arrange
    answers = [
        _answer(1, stable=True, stable_evidence="Full-time", admits_location=True),
        _answer(
            0,
            work_mode="remote",
            work_mode_evidence="Fully remote",
            admits_location=True,
            admits_location_evidence="Hiring across Europe",
        ),
    ]

    # Act
    readings = _read(tmp_path, result({"offers": answers}))

    # Assert
    assert readings == [
        Reading(
            work_mode=WorkMode.REMOTE,
            work_mode_evidence="Fully remote",
            admits_location=True,
            admits_location_evidence="Hiring across Europe",
        ),
        # Asked without a location: what it says of one is dropped.
        Reading(stable=True, stable_evidence="Full-time"),
    ]


@pytest.mark.parametrize(
    "answers",
    [
        pytest.param([_answer(0)], id="missing"),
        pytest.param([_answer(0), _answer(1, work_mode="anywhere")], id="not a work mode"),
        pytest.param([_answer(0), _answer(1, stable="yes")], id="not a boolean"),
    ],
)
def test_an_offer_claude_does_not_answer_for_rightly_is_an_error(
    tmp_path: Path, answers: list[dict[str, Any]]
) -> None:
    # Act
    readings = _read(tmp_path, result({"offers": answers}))

    # Assert
    assert readings[0] == Reading()
    assert isinstance(readings[1], OfferReaderError)


def test_asks_claude_about_every_offer_numbered_with_no_tools(tmp_path: Path) -> None:
    # Act
    _read(tmp_path, result({"offers": []}))

    # Assert
    told = asked(tmp_path)
    args = told["args"]
    assert args[args.index("--model") + 1] == "sonnet"
    assert args[args.index("--tools") + 1] == ""
    assert '"offers"' in args[args.index("--json-schema") + 1]
    assert "Posting 0\nLocation to answer admits_location for: Spain" in told["stdin"]
    assert "Posting 1\nTitle: Data Engineer" in told["stdin"]


@pytest.mark.parametrize(
    ("stdout", "code"),
    [
        pytest.param(result({"offers": []}), 1, id="exit code"),
        pytest.param(result(None, is_error=True), 0, id="error result"),
        pytest.param("not json", 0, id="not json"),
        pytest.param(result({"work_mode": "remote"}), 0, id="not the schema"),
        pytest.param("[]", 0, id="not an object"),
    ],
)
def test_a_failed_request_is_a_reader_error(tmp_path: Path, stdout: str, code: int) -> None:
    # Act / Assert
    with pytest.raises(OfferReaderError):
        _read(tmp_path, stdout, code)


@pytest.mark.parametrize(
    ("reader", "groq_key", "claude", "expected"),
    [
        pytest.param("groq", "key", None, OfferReader, id="Groq"),
        pytest.param("groq", "", "/bin/claude", None, id="Groq without its key"),
        pytest.param("claude-code", "", "/bin/claude", ClaudeCodeReader, id="Claude Code"),
        pytest.param("claude-code", "key", None, None, id="Claude Code, not installed"),
    ],
)
def test_the_configured_reader_runs_only_when_it_can(  # noqa: PLR0913, PLR0917  # the cases
    monkeypatch: pytest.MonkeyPatch,
    reader: str,
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
        offer_reader=reader,  # type: ignore[arg-type]  # the cases name valid ones
    )

    # Act
    chosen = offer_reader(settings, httpx2.AsyncClient())

    # Assert
    assert (type(chosen) if chosen else None) is expected
