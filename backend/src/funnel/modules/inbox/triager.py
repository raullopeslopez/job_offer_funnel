"""The offer triager: a language model on Groq that compares pending offers with what the
user decided before, and suggests discarding the ones they would discard.

One chat completion per batch of offers, answered as JSON with a strict schema, like the
offer reader (reader.py). The context (profiles, decisions, its own mistakes) goes once
per request, which is what makes a batch cheaper than one request per offer. What the
model answers is not trusted: the domain keeps only the suggestions whose evidence holds.
"""

import json
from collections.abc import Mapping, Sequence
from typing import Any, Final

import httpx2

from funnel.modules.inbox.domain import (
    SUGGESTED_REASONS,
    Decision,
    Mistake,
    OfferStatus,
    OfferText,
    OfferTriagerError,
    TriageAnswer,
    TriageContext,
    TriageMistake,
)
from funnel.modules.inbox.reader import API

# The free plan allows 8,000 tokens a minute: five descriptions must fit with the context.
_HEAD_CHARACTERS: Final = 2000
_TAIL_CHARACTERS: Final = 500

_INSTRUCTIONS: Final = f"""\
You help a job seeker triage job offers. You are given their search profiles, the offers \
they promoted and discarded before (with why), the mistakes you made before, and some new \
offers. For each new offer, say whether they would discard it, judging only by what they \
decided before. When in doubt, say nothing: a wrong suggestion costs more than a missed one.
Answer for every offer, by its number. To suggest a discard give a reason and its evidence:
- title_word: a word of the title they keep discarding; the evidence is that word, copied \
from the title.
- stack, location, contract or company: the evidence is one short excerpt copied character \
by character from the description that shows it.
Reasons: {", ".join(sorted(SUGGESTED_REASONS))}. With nothing to say, answer null for the \
reason and the evidence. Learn from your mistakes: do not suggest again what they promoted, \
and look for what you missed."""

_SCHEMA: Final = {
    "type": "object",
    "properties": {
        "offers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "offer": {"type": "integer"},
                    "reason": {
                        "type": ["string", "null"],
                        "enum": [*sorted(SUGGESTED_REASONS), None],
                    },
                    "evidence": {"type": ["string", "null"]},
                },
                "required": ["offer", "reason", "evidence"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["offers"],
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
        f"Description:\n{_excerpt(offer.description)}"
        for number, offer in enumerate(offers)
    ]
    sections = (
        ("Search profiles", profiles),
        ("Decisions, the most recent first", [_decision(d) for d in context.decisions]),
        ("Your mistakes, the most recent first", [_mistake(m) for m in context.mistakes]),
    )
    told = "\n\n".join(f"{title}:\n" + ("\n".join(lines) or "none") for title, lines in sections)
    return f"{told}\n\nNew offers:\n\n" + "\n\n".join(new)


def _answers(answer: Any, offers: int) -> dict[int, TriageAnswer]:
    if not isinstance(answer, dict) or not isinstance(answer.get("offers"), list):
        raise TypeError(f"expected an object with offers, got {answer!r}")
    found: dict[int, TriageAnswer] = {}
    for item in answer["offers"]:
        number = item.get("offer") if isinstance(item, dict) else None
        if isinstance(number, int) and 0 <= number < offers:
            reason, evidence = item.get("reason"), item.get("evidence")
            found[number] = TriageAnswer(
                reason=reason if isinstance(reason, str) else None,
                evidence=evidence if isinstance(evidence, str) else None,
            )
    return found


class OfferTriager:
    """Asks the model about a batch of offers at a time."""

    def __init__(self, client: httpx2.AsyncClient, api_key: str, model: str) -> None:
        self._client = client
        self._api_key = api_key
        self._model = model

    async def triage(
        self, offers: Sequence[OfferText], context: TriageContext
    ) -> Mapping[int, TriageAnswer]:
        """What the model says of each offer, by its position; an offer it did not answer
        for is missing. Raises OfferTriagerError when the model does not answer (network,
        quota, error status) or answers something that is not the JSON asked for."""
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
            return _answers(answer, len(offers))
        except (httpx2.HTTPError, ValueError, KeyError, IndexError, TypeError) as error:
            raise OfferTriagerError(f"{type(error).__name__}: {error}") from error
