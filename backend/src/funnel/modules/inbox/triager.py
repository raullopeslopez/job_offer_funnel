"""The offer triager: a language model on Groq that compares pending offers with what the
user decided before, marks each one OK or KO (a false positive) with why, suggests
discarding the KO ones, and suggests words to exclude from the profiles.

One chat completion per batch of offers, answered as JSON with a strict schema, like the
offer reader (reader.py). The context (profiles, decisions, its own mistakes) goes once
per request, which is what makes a batch cheaper than one request per offer. What the
model answers is not trusted: the domain keeps only the suggestions whose evidence holds.
"""

import json
from collections.abc import Sequence
from typing import Any, Final

import httpx2

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

# The free plan allows 8,000 tokens a minute: five descriptions must fit with the context.
_HEAD_CHARACTERS: Final = 2000
_TAIL_CHARACTERS: Final = 500

_INSTRUCTIONS: Final = f"""\
You help a job seeker triage job offers. You are given their search profiles, the offers \
they promoted and discarded before (with why), the mistakes you made before, and some new \
offers that passed their filters. Judge each new offer only by what they decided before.
Answer for every offer, by its number, with a verdict and why:
- ok: worth their time.
- ko: a false positive: it passed their filters but they would discard it.
When in doubt, say ok: a wrong ko costs more than a missed one. Why is one short sentence.
For a ko, give the reason and its evidence:
- title_word: a word of the title they keep discarding; the evidence is that word, copied \
from the title.
- stack, location, contract or company: the evidence is one short excerpt copied character \
by character from the description that shows it.
Reasons: {", ".join(sorted(SUGGESTED_REASONS))}; for an ok, null reason and evidence.
Some new offers are near misses: their filters stopped them, by the one rule told with \
each. For those, ok is a false negative (the rule stopped an offer worth their time) and \
ko means rightly filtered; give no reason for them.
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
                    "why": {"type": "string"},
                    "reason": {
                        "type": ["string", "null"],
                        "enum": [*sorted(SUGGESTED_REASONS), None],
                    },
                    "evidence": {"type": ["string", "null"]},
                },
                "required": ["offer", "verdict", "why", "reason", "evidence"],
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
        return f"- promoted: {decision.title}"
    word = f" ({decision.word})" if decision.word else ""
    return f"- discarded, {decision.reason}{word}: {decision.title}"


def _mistake(mistake: TriageMistake) -> str:
    if mistake.mistake is Mistake.MISSED_DISCARD:
        return f"- you missed this discard: {mistake.title}"
    return f"- you suggested {mistake.reason} and they promoted it: {mistake.title}"


def _filtered_by(check: RuleCheck | None) -> str:
    """The rule that stopped a near miss, with what explains it."""
    if check is None:
        return ""
    if check.rule is Rule.EXCLUDED:
        why = f"it has the excluded word {_listed(check.found)}"
    elif check.rule is Rule.KEYWORDS:
        why = f"it lacks the keywords {_listed(check.missing)}"
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
        f"excluded {_listed(terms.excluded_keywords)}"
        for terms in context.profiles
    ]
    new = [
        f"Offer {number}\nTitle: {offer.title}\nCompany: {offer.company}\n"
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
                why=_text(item.get("why")),
                reason=_text(item.get("reason")),
                evidence=_text(item.get("evidence")),
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


class OfferTriager:
    """Asks the model about a batch of offers at a time."""

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
