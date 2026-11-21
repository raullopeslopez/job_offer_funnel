"""The offer reader: a language model, on Groq or on Claude Code, that says what a job
description states.

On Groq, one chat completion per offer and location, answered as JSON with a strict
schema (https://console.groq.com/docs/structured-outputs, checked on 2026-11-12). The free
plan allows 8,000 tokens a minute for the default model, so the text sent is capped. On
Claude Code (claude_code.py), one request per batch of offers, told and answering the
same. What the model answers is not trusted: the domain keeps only the answers whose
evidence is in the description.
"""

import json
from collections.abc import Sequence
from typing import Any, Final, Protocol

import httpx2

from funnel.modules.discovery.domain import WorkMode
from funnel.modules.inbox import claude_code
from funnel.modules.inbox.domain import OfferReaderError, OfferText, Reading

API: Final = "https://api.groq.com/openai/v1/chat/completions"
# A description says where and how the work is done at its start or at its end.
_HEAD_CHARACTERS: Final = 3500
_TAIL_CHARACTERS: Final = 1500

_INSTRUCTIONS: Final = """\
You read a job posting and answer only with what it states explicitly. Never guess.
For every answer give as evidence one short excerpt copied character by character from \
the title, the location or the description. If none of them states something, answer \
null for it and for its evidence.
- work_mode: where the work is done, never what the role is about. "remote" if it can be \
done fully from home, also when an office is optional, when remote is one of the options \
offered, or when it only asks for occasional travel; "hybrid" only if it requires regular \
days in an office; "onsite" only if it requires working at an office or site. Where the \
company or its team is does not make a job hybrid or onsite.
- admits_location: true only if the description states where the job can be done from and \
that includes the given location (it names that place, or a region that contains it, or \
says anywhere or worldwide); false only if it requires living, being a citizen or having \
the right to work somewhere that excludes the given location. Otherwise null: a job that \
is just "remote", preferred locations, working hours or time zones, languages, the \
salary's currency, and where the company, its team or its clients are, are not \
requirements. But a remote job whose title or location names a place, in any spelling \
("Backend Engineer - UK", "US Remote", "USA only", "Remote, Germany"), can only be done \
living there: answer false if that place excludes the given location, quoting it, unless \
the description opens the job to other places.
- stable: true if it is a full-time position with no end date, as an employee or as a \
contractor; false if it is freelance, paid by the task or by the hour (an hourly or per \
task rate makes it false even if it says full-time), temporary, or part-time. Weekly \
hours or a salary alone say nothing: null.
- engineering: true if the role is mainly building software (writing and shipping code), \
in a product team or with customers, as a forward deployed engineer who builds can be; \
false if it is mainly sales, pre-sales, solutions or sales engineering, customer support, \
consulting, or product or project management, whatever its title says.
- stack: the programming languages and frameworks the role mainly works with, at most \
five, each written as in the evidence; not every tool, cloud or database the posting \
names, and not those it only mentions in passing or as a plus. The evidence is one \
excerpt that names all of them. Empty and null evidence if it names none."""


def _nullable(json_type: str, **keywords: Any) -> dict[str, Any]:
    return {"type": [json_type, "null"], **keywords}


def _schema(asks_location: bool) -> dict[str, Any]:
    properties = {
        "work_mode": _nullable("string", enum=[*(mode.value for mode in WorkMode), None]),
        "work_mode_evidence": _nullable("string"),
        "stable": _nullable("boolean"),
        "stable_evidence": _nullable("string"),
        "engineering": _nullable("boolean"),
        "engineering_evidence": _nullable("string"),
        "stack": {"type": "array", "items": {"type": "string"}},
        "stack_evidence": _nullable("string"),
    }
    if asks_location:
        properties |= {
            "admits_location": _nullable("boolean"),
            "admits_location_evidence": _nullable("string"),
        }
    # Strict mode needs every property required and no others.
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def _excerpt(description: str) -> str:
    if len(description) <= _HEAD_CHARACTERS + _TAIL_CHARACTERS:
        return description
    return f"{description[:_HEAD_CHARACTERS]}\n[...]\n{description[-_TAIL_CHARACTERS:]}"


def _question(offer: OfferText, location: str | None) -> str:
    asked = "" if location is None else f"Location to answer admits_location for: {location}\n"
    published = "" if offer.location is None else f"Location: {offer.location}\n"
    return (
        f"{asked}Title: {offer.title}\nCompany: {offer.company}\n{published}"
        f"Description:\n{_excerpt(offer.description)}"
    )


def _optional[T](value: object, expected: type[T]) -> T | None:
    if value is None:
        return None
    if not isinstance(value, expected):
        raise TypeError(f"expected {expected.__name__}, got {value!r}")
    return value


def _reading(answer: dict[str, Any]) -> Reading:
    work_mode = _optional(answer.get("work_mode"), str)
    return Reading(
        work_mode=None if work_mode is None else WorkMode(work_mode),
        work_mode_evidence=_optional(answer.get("work_mode_evidence"), str),
        admits_location=_optional(answer.get("admits_location"), bool),
        admits_location_evidence=_optional(answer.get("admits_location_evidence"), str),
        stable=_optional(answer.get("stable"), bool),
        stable_evidence=_optional(answer.get("stable_evidence"), str),
        engineering=_optional(answer.get("engineering"), bool),
        engineering_evidence=_optional(answer.get("engineering_evidence"), str),
        stack=_names(answer.get("stack")),
        stack_evidence=_optional(answer.get("stack_evidence"), str),
    )


def _names(value: object) -> tuple[str, ...]:
    names = _optional(value, list) or []
    if not all(isinstance(name, str) for name in names):
        raise TypeError(f"expected a list of strings, got {value!r}")
    return tuple(names)


# An offer to read and the location to ask about, if any.
type Question = tuple[OfferText, str | None]


class Reader(Protocol):
    batch_size: int

    async def read_batch(self, questions: Sequence[Question]) -> list[Reading | OfferReaderError]:
        """What the posting says of each offer, by its position, or why it was not read.
        Raises OfferReaderError when the whole request fails."""
        ...


class OfferReader:
    """Asks the model on Groq about one offer at a time."""

    # The free plan allows about this many readings a minute.
    batch_size = 5

    def __init__(self, client: httpx2.AsyncClient, api_key: str, model: str) -> None:
        self._client = client
        self._api_key = api_key
        self._model = model

    async def read(self, offer: OfferText, location: str | None) -> Reading:
        """What the posting says, for someone living in `location` if there is one.

        Raises OfferReaderError when the model does not answer (network, quota, error
        status) or answers something that is not the JSON asked for.
        """
        body = {
            "model": self._model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": _INSTRUCTIONS},
                {"role": "user", "content": _question(offer, location)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "offer_reading",
                    "strict": True,
                    "schema": _schema(asks_location=location is not None),
                },
            },
        }
        try:
            response = await self._client.post(
                API, json=body, headers={"Authorization": f"Bearer {self._api_key}"}
            )
            response.raise_for_status()
            answer = json.loads(response.json()["choices"][0]["message"]["content"])
            if not isinstance(answer, dict):
                raise TypeError(f"expected an object, got {answer!r}")
            return _reading(answer)
        except (httpx2.HTTPError, ValueError, KeyError, IndexError, TypeError) as error:
            raise OfferReaderError(f"{type(error).__name__}: {error}") from error

    async def read_batch(self, questions: Sequence[Question]) -> list[Reading | OfferReaderError]:
        """Each offer in its own request: one that fails leaves the others read."""
        answers: list[Reading | OfferReaderError] = []
        for offer, location in questions:
            try:
                answers.append(await self.read(offer, location))
            except OfferReaderError as error:
                answers.append(error)
        return answers


_BATCH_INSTRUCTIONS: Final = f"""\
{_INSTRUCTIONS}
You are given several numbered postings. Answer for every one, by its number, with what \
that posting states. A posting with no location to answer for gets null admits_location \
and null admits_location_evidence."""


def _batch_schema() -> dict[str, Any]:
    reading = _schema(asks_location=True)
    item = reading | {
        "properties": {"offer": {"type": "integer"}, **reading["properties"]},
        "required": ["offer", *reading["required"]],
    }
    return {
        "type": "object",
        "properties": {"offers": {"type": "array", "items": item}},
        "required": ["offers"],
        "additionalProperties": False,
    }


def _batch_question(questions: Sequence[Question]) -> str:
    # Without a location to answer for, the question says none: its answer is dropped.
    return "\n\n".join(
        f"Posting {number}\n{_question(offer, location)}"
        for number, (offer, location) in enumerate(questions)
    )


def _batch_answers(
    answer: object, questions: Sequence[Question]
) -> list[Reading | OfferReaderError]:
    if not isinstance(answer, dict) or not isinstance(answer.get("offers"), list):
        raise TypeError(f"expected an object with offers, got {answer!r}")
    found: dict[int, dict[str, Any]] = {
        item["offer"]: item
        for item in answer["offers"]
        if isinstance(item, dict) and isinstance(item.get("offer"), int)
    }
    answers: list[Reading | OfferReaderError] = []
    for number, (_offer, location) in enumerate(questions):
        item = found.get(number)
        if item is None:
            answers.append(OfferReaderError(f"no answer for posting {number}"))
            continue
        if location is None:
            item = {**item, "admits_location": None, "admits_location_evidence": None}
        try:
            answers.append(_reading(item))
        except (TypeError, ValueError) as error:
            answers.append(OfferReaderError(f"{type(error).__name__}: {error}"))
    return answers


class ClaudeCodeReader:
    """Asks Claude about a batch of offers at a time through the `claude` CLI."""

    # No per-minute token plan to fit in: the batch is as large as stays quick to answer.
    batch_size = 20

    def __init__(self, command: Sequence[str], model: str) -> None:
        self._command = list(command)
        self._model = model

    async def read_batch(self, questions: Sequence[Question]) -> list[Reading | OfferReaderError]:
        """What the posting says of each offer, by its position; an offer Claude does not
        answer for, or answers wrongly, is an error. Raises OfferReaderError when the
        request fails."""
        try:
            answer = await claude_code.ask(
                self._command,
                self._model,
                _BATCH_INSTRUCTIONS,
                _batch_schema(),
                _batch_question(questions),
            )
            return _batch_answers(answer, questions)
        except claude_code.FAILURES as error:
            raise OfferReaderError(f"{type(error).__name__}: {error}") from error
