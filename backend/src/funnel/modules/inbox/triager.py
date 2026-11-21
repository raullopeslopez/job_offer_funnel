"""The offer triager: a language model, on Groq or on Claude Code, that compares pending
offers with what the user decided before, marks each one OK or KO (a false positive) with
why yes, why not and its confidence, suggests discarding the KO ones, and suggests words
to exclude from the profiles.

One request per batch of offers, answered as JSON with a strict schema: a chat completion
on Groq, like the offer reader (reader.py), or the `claude` CLI on the user's Claude
subscription, which only runs where it is installed and signed in. Both are told and
answer the same. The context (profiles, decisions, its own mistakes) goes once
per request, which is what makes a batch cheaper than one request per offer. What the
model answers is not trusted: the domain keeps only the suggestions whose evidence holds.
"""

import json
from collections.abc import Sequence
from typing import Any, Final, Protocol

import httpx2

from funnel.modules.inbox import claude_code
from funnel.modules.inbox.domain import (
    SUGGESTED_REASONS,
    Decision,
    Mistake,
    OfferStatus,
    OfferText,
    OfferTriagerError,
    Rule,
    RuleCheck,
    TriageAnswer,
    TriageContext,
    TriageMistake,
    TriageReply,
    TriagerSuggestion,
)
from funnel.modules.inbox.reader import API

# The part of each description told: the head says the role, the tail often the location.
_HEAD_CHARACTERS: Final = 2000
_TAIL_CHARACTERS: Final = 500

_INSTRUCTIONS: Final = f"""\
You help a job seeker triage job offers. You are given their search profiles, the offers \
they promoted and discarded before (with why), the mistakes you made before, and some new \
offers that passed their filters.
The filters only match words, so an offer can pass them and still be a job they do not want. \
Each profile says what they want: its titles name the kind of role, and its excluded words \
name what they do not want (for example iOS or Android: no mobile work; Frontend: no \
frontend work; DevOps or SRE: no operations work). Judge each new offer by the work it \
actually describes (its main stack, platform and duties), not only by the words of its \
title, and by what they decided before.
Answer for every offer, by its number, with a verdict, why yes, why not and your \
confidence:
- ok: its main work is the kind of role of one of their profiles.
- ko: a false positive: its main work is something their profiles do not want, or like \
what they discarded before.
When the description really leaves it open, say ok: a wrong ko costs more than a missed \
one. An offer whose main work is plainly of a kind they do not want is not in doubt.
Why yes is what in the offer speaks for it, and why not what speaks against it, whatever \
the verdict: each one short sentence that names what in the offer it is (its stack, \
platform, duties, location or contract), never a general phrase like "worth their time"; \
null when there is really nothing to say on that side. With each, give a quote: a short \
excerpt copied character by character from the title or the description that shows it, \
or null.
Confidence is low, medium or high: how sure you are of the verdict. Say high only when \
the offer plainly says what decides it.
For a ko, give the reason and its evidence:
- title_word: a word of the title they keep discarding; the evidence is that word, copied \
from the title.
- stack, location, contract or company: the evidence is one short excerpt copied character \
by character from the description that shows it.
Reasons: {", ".join(sorted(SUGGESTED_REASONS))}; for an ok, null reason and evidence.
Some new offers are near misses: their title fits a profile, and their filters stopped \
them by the one rule told with each. For those, judge that rule, not the role: the title \
already fits, so what the role is decides nothing. ok is a false negative: the rule is \
wrong for this offer, and its description shows it. Then why yes says why the rule is \
wrong, and its quote is a sentence of at least four words copied character by character \
from the description that shows it; for the location rule, one that says the job can be \
done remotely while living in the profile's location. Where a job can be done from is \
decided by what its description says, never by the words of its title, and its published \
location is what made the rule fail, so it never rebuts it. Without such a quote, say ko: \
rightly filtered. Give no reason for near misses.
Then, to make their filters better, you may suggest words to exclude from a profile: a \
word that is in the ko offers you name and in the offers they discarded, and in none they \
promoted. Give the profile's name, the word, why, and the numbers of those ko offers. \
Suggest none rather than a doubtful one.
Learn from your mistakes: do not mark ko again what they promoted, and look for what you \
missed."""

_SCHEMA: Final = {
    "type": "object",
    "properties": {
        "offers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "offer": {"type": "integer"},
                    "verdict": {"type": "string", "enum": ["ok", "ko"]},
                    "why_yes": {"type": ["string", "null"]},
                    "quote_yes": {"type": ["string", "null"]},
                    "why_not": {"type": ["string", "null"]},
                    "quote_not": {"type": ["string", "null"]},
                    "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                    "reason": {
                        "type": ["string", "null"],
                        "enum": [*sorted(SUGGESTED_REASONS), None],
                    },
                    "evidence": {"type": ["string", "null"]},
                },
                "required": [
                    "offer",
                    "verdict",
                    "why_yes",
                    "quote_yes",
                    "why_not",
                    "quote_not",
                    "confidence",
                    "reason",
                    "evidence",
                ],
                "additionalProperties": False,
            },
        },
        "exclusions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "profile": {"type": "string"},
                    "word": {"type": "string"},
                    "why": {"type": "string"},
                    "offers": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["profile", "word", "why", "offers"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["offers", "exclusions"],
    "additionalProperties": False,
}


def _excerpt(description: str) -> str:
    if len(description) <= _HEAD_CHARACTERS + _TAIL_CHARACTERS:
        return description
    return f"{description[:_HEAD_CHARACTERS]}\n[...]\n{description[-_TAIL_CHARACTERS:]}"


def _decision(decision: Decision) -> str:
    if decision.status is OfferStatus.PROMOTED:
        return f'- promoted: "{decision.title}"'
    word = f", word {decision.word}" if decision.word else ""
    # The reason apart from the title: "discarded, location: <title>" was read as a place.
    return f'- discarded (reason: {decision.reason}{word}): "{decision.title}"'


def _mistake(mistake: TriageMistake) -> str:
    if mistake.mistake is Mistake.MISSED_DISCARD:
        return f"- you missed this discard: {mistake.title}"
    return f"- you suggested {mistake.reason} and they promoted it: {mistake.title}"


def _filtered_by(check: RuleCheck | None) -> str:
    """The rule that stopped a near miss, with what explains it."""
    if check is None:
        return ""
    if check.rule is Rule.EXCLUDED and check.evidence:
        why = f'its main stack has the excluded word {_listed(check.found)} ("{check.evidence}")'
    elif check.rule is Rule.EXCLUDED:
        why = f"it has the excluded word {_listed(check.found)}"
    elif check.rule is Rule.ENGINEERING:
        why = f'it is not an engineering job ("{check.evidence}")'
    elif check.rule is Rule.KEYWORDS:
        why = f"it lacks the keywords {_listed(check.missing)}"
    elif check.rule is Rule.LOCATION:
        why = f'it is not open to the profile\'s location ("{check.evidence}")'
    else:
        why = f"its description says {check.value}" + (
            f' ("{check.evidence}")' if check.evidence else ""
        )
    return f"Near miss, filtered by {check.rule}: {why}\n"


def _listed(words: Sequence[str]) -> str:
    return ", ".join(words) or "none"


def _question(offers: Sequence[OfferText], context: TriageContext) -> str:
    profiles = [
        f"- {terms.name}: titles {_listed(terms.titles)}; keywords {_listed(terms.keywords)}; "
        f"excluded {_listed(terms.excluded_keywords)}; location {terms.location or 'any'}; "
        f"work modes {_listed(terms.work_modes)}"
        for terms in context.profiles
    ]
    new = [
        f"Offer {number}\nTitle: {offer.title}\nCompany: {offer.company}\n"
        f"Location: {offer.location or 'not published'}\n"
        f"{_filtered_by(offer.filtered_by)}Description:\n{_excerpt(offer.description)}"
        for number, offer in enumerate(offers)
    ]
    sections = (
        ("Search profiles", profiles),
        ("Decisions, the most recent first", [_decision(d) for d in context.decisions]),
        ("Your mistakes, the most recent first", [_mistake(m) for m in context.mistakes]),
    )
    told = "\n\n".join(f"{title}:\n" + ("\n".join(lines) or "none") for title, lines in sections)
    return f"{told}\n\nNew offers:\n\n" + "\n\n".join(new)


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _reply(answer: Any, offers: int) -> TriageReply:
    if not isinstance(answer, dict) or not isinstance(answer.get("offers"), list):
        raise TypeError(f"expected an object with offers, got {answer!r}")
    found: dict[int, TriageAnswer] = {}
    for item in answer["offers"]:
        number = item.get("offer") if isinstance(item, dict) else None
        if isinstance(number, int) and 0 <= number < offers:
            found[number] = TriageAnswer(
                verdict=_text(item.get("verdict")),
                why_yes=_text(item.get("why_yes")),
                why_not=_text(item.get("why_not")),
                reason=_text(item.get("reason")),
                evidence=_text(item.get("evidence")),
                quote_yes=_text(item.get("quote_yes")),
                quote_not=_text(item.get("quote_not")),
                confidence=_text(item.get("confidence")),
            )
    exclusions = answer.get("exclusions")
    suggestions = [
        TriagerSuggestion(
            item["profile"],
            item["word"],
            _text(item.get("why")) or "",
            [n for n in item.get("offers") or [] if isinstance(n, int)],
        )
        for item in (exclusions if isinstance(exclusions, list) else [])
        if isinstance(item, dict) and _text(item.get("profile")) and _text(item.get("word"))
    ]
    return TriageReply(found, suggestions)


class Triager(Protocol):
    batch_size: int

    async def triage(self, offers: Sequence[OfferText], context: TriageContext) -> TriageReply:
        """What the model says of each offer, by its position (an offer it did not answer
        for is missing), and the exclusions it suggests. Raises OfferTriagerError when the
        model does not answer or answers something that is not the JSON asked for."""
        ...


class OfferTriager:
    """Asks the model on Groq about a batch of offers at a time."""

    # The free plan allows 8,000 tokens a minute: five descriptions must fit with the context.
    batch_size = 5

    def __init__(self, client: httpx2.AsyncClient, api_key: str, model: str) -> None:
        self._client = client
        self._api_key = api_key
        self._model = model

    async def triage(self, offers: Sequence[OfferText], context: TriageContext) -> TriageReply:
        """What the model says of each offer, by its position (an offer it did not answer
        for is missing), and the exclusions it suggests. Raises OfferTriagerError when the
        model does not answer (network, quota, error status) or answers something that is
        not the JSON asked for."""
        body = {
            "model": self._model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": _INSTRUCTIONS},
                {"role": "user", "content": _question(offers, context)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "offer_triage", "strict": True, "schema": _SCHEMA},
            },
        }
        try:
            response = await self._client.post(
                API, json=body, headers={"Authorization": f"Bearer {self._api_key}"}
            )
            response.raise_for_status()
            answer = json.loads(response.json()["choices"][0]["message"]["content"])
            return _reply(answer, len(offers))
        except (httpx2.HTTPError, ValueError, KeyError, IndexError, TypeError) as error:
            raise OfferTriagerError(f"{type(error).__name__}: {error}") from error


class ClaudeCodeTriager:
    """Asks Claude about a batch of offers at a time through the `claude` CLI, with no
    tools, no settings, no MCP servers and no saved session, from an empty folder: it
    only sees what it is told."""

    # No per-minute token plan to fit in: the batch is as large as stays quick to answer.
    batch_size = 20

    def __init__(self, command: Sequence[str], model: str) -> None:
        self._command = list(command)
        self._model = model

    async def triage(self, offers: Sequence[OfferText], context: TriageContext) -> TriageReply:
        try:
            answer = await claude_code.ask(
                self._command, self._model, _INSTRUCTIONS, _SCHEMA, _question(offers, context)
            )
            return _reply(answer, len(offers))
        except claude_code.FAILURES as error:
            raise OfferTriagerError(f"{type(error).__name__}: {error}") from error
