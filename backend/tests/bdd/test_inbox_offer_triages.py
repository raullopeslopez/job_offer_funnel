import re
from collections.abc import AsyncIterator, Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when
from support.clock import FixedClock
from support.triages import said

from funnel.core.clock import get_clock
from funnel.modules.inbox.domain import (
    OfferText,
    OfferTriagerError,
    TriageAnswer,
    TriageContext,
    TriageReply,
    TriagerSuggestion,
)
from funnel.modules.inbox.router import get_feed_client, get_offer_triager

pytestmark = pytest.mark.bdd

scenarios("inbox/offer_triages.feature")

OFFERS_URL = "/api/v1/offers"
TRIAGES_URL = f"{OFFERS_URL}/triages"
SUGGESTIONS_URL = "/api/v1/criteria-suggestions"
PROFILES_URL = "/api/v1/search-profiles"
LIST_FIELDS = frozenset({"titles", "keywords", "excluded_keywords"})
# Past the 6 hours a job board waits between imports.
LATER = timedelta(hours=7)

Row = dict[str, str]


@dataclass
class ScenarioState:
    remoteok: list[Row] = field(default_factory=list)
    remoteok_id: str | None = None
    imports: int = 0
    # What the fake triager answers, by company (OK when the scenario says nothing); the
    # exclusions it suggests, with the companies they come from; those it leaves out;
    # whether it fails.
    answers: dict[str, TriageAnswer] = field(default_factory=dict)
    suggestions: list[tuple[str, str, str, list[str]]] = field(default_factory=list)
    unanswered: set[str] = field(default_factory=set)
    is_failing: bool = False
    # Groq, Claude Code, Claude Code not installed, or missing.
    triager: str = "Groq"
    # What it was asked: the offers and the context of each request.
    requests: list[tuple[list[OfferText], TriageContext]] = field(default_factory=list)
    response: httpx2.Response | None = None

    @property
    def last_response(self) -> httpx2.Response:
        assert self.response is not None, "no request was made in this scenario"
        return self.response

    @property
    def last_request(self) -> tuple[list[OfferText], TriageContext]:
        assert self.requests, "the offer triager was not asked"
        return self.requests[-1]


@pytest.fixture
def state() -> ScenarioState:
    return ScenarioState()


# How many offers each offer triager takes at a time (specs/inbox/offer_triages.feature).
BATCH_SIZES = {"Groq": 5, "Claude Code": 20}


class FakeOfferTriager:
    """Answers what the scenario says; an offer it knows nothing about is OK."""

    def __init__(self, state: ScenarioState) -> None:
        self._state = state
        self.batch_size = BATCH_SIZES[state.triager]

    async def triage(self, offers: Sequence[OfferText], context: TriageContext) -> TriageReply:
        self._state.requests.append((list(offers), context))
        if self._state.is_failing:
            raise OfferTriagerError("the triager is down")
        answers: Mapping[int, TriageAnswer] = {
            number: self._state.answers.get(offer.company, TriageAnswer("ok", "Fits."))
            for number, offer in enumerate(offers)
            if offer.company not in self._state.unanswered
        }
        numbers = {offer.company: number for number, offer in enumerate(offers)}
        suggestions = [
            TriagerSuggestion(profile, word, why, [numbers[c] for c in companies if c in numbers])
            for profile, word, why, companies in self._state.suggestions
        ]
        return TriageReply(answers, suggestions)


@pytest.fixture(autouse=True)
def fake_sources(client: TestClient, state: ScenarioState) -> Iterator[None]:
    """Remote OK and the offer triager answer from the scenario: tests never reach the
    internet."""

    def answer(_request: httpx2.Request) -> httpx2.Response:
        jobs = [
            {
                "position": r["title"],
                "company": r["company"],
                "description": r["description"],
                "url": r["url"],
            }
            for r in state.remoteok
        ]
        return httpx2.Response(200, json=[{"legal": "Link back to Remote OK."}, *jobs])

    async def fake_client() -> AsyncIterator[httpx2.AsyncClient]:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(answer)) as fake:
            yield fake

    overrides = cast(FastAPI, client.app).dependency_overrides
    overrides[get_feed_client] = fake_client
    overrides[get_offer_triager] = lambda: (
        FakeOfferTriager(state) if state.triager in BATCH_SIZES else None
    )
    yield
    overrides.pop(get_feed_client, None)
    overrides.pop(get_offer_triager, None)
    overrides.pop(get_clock, None)


def _ok(response: httpx2.Response, status: int = 201) -> dict[str, Any]:
    assert response.status_code == status, response.text
    body: dict[str, Any] = response.json() if response.content else {}
    return body


def _rows(datatable: list[list[str]]) -> list[Row]:
    header, *rows = datatable
    return [dict(zip(header, values, strict=True)) for values in rows]


def _offer(client: TestClient, company: str) -> dict[str, Any]:
    items = _ok(client.get(OFFERS_URL, params={"limit": "100"}), 200)["items"]
    offer: dict[str, Any] = next(o for o in items if o["company"] == company)
    return offer


def _profile(client: TestClient, name: str) -> dict[str, Any]:
    items = _ok(client.get(PROFILES_URL, params={"limit": "100"}), 200)["items"]
    profile: dict[str, Any] = next(p for p in items if p["name"] == name)
    return profile


def _suggestions(client: TestClient) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = _ok(client.get(SUGGESTIONS_URL), 200)["items"]
    return items


def _suggestion(client: TestClient, word: str, profile: str) -> dict[str, Any] | None:
    return next(
        (
            s
            for s in _suggestions(client)
            if s["word"].casefold() == word.casefold()
            and s["search_profile_name"] == profile
            and s["rule"] == "excluded_keywords"
        ),
        None,
    )


def _offer_url(client: TestClient, company: str) -> str:
    return f"{OFFERS_URL}/{_offer(client, company)['id']}"


def _import(client: TestClient, state: ScenarioState) -> None:
    # Each import a few hours after the last one, so the job board's wait never stops it.
    clock = FixedClock(datetime.now(UTC) + LATER * state.imports)
    cast(FastAPI, client.app).dependency_overrides[get_clock] = lambda: clock
    state.imports += 1
    _ok(client.post(f"/api/v1/job-boards/{state.remoteok_id}/imports"))


# --- Given ---


@given(parsers.parse('a job board named "Remote OK" imported from the feed "remoteok"'))
def given_remoteok_job_board(client: TestClient, state: ScenarioState) -> None:
    body = {
        "name": "Remote OK",
        "search_url_template": "https://remoteok.com/?q={query}",
        "syntax": "keywords",
        "import_method": "api",
        "feed": "remoteok",
    }
    state.remoteok_id = _ok(client.post("/api/v1/job-boards", json=body))["id"]


@given(parsers.parse('a search profile named "{name}" with:'))
def given_profile(client: TestClient, name: str, datatable: list[list[str]]) -> None:
    body: dict[str, Any] = {"name": name}
    for key, value in datatable:
        body[key] = re.split(r"\s*,\s*", value) if key in LIST_FIELDS else value
    _ok(client.post("/api/v1/search-profiles", json=body))


@given(parsers.parse('the job board "Remote OK" was imported with:'))
def given_imported(client: TestClient, state: ScenarioState, datatable: list[list[str]]) -> None:
    # The feed keeps publishing what it published before: those offers are not expired.
    state.remoteok = [*state.remoteok, *_rows(datatable)]
    _import(client, state)


@given(
    parsers.parse('the job board "Remote OK" was imported with {number:d} more offers as "{title}"')
)
def given_more_imported(client: TestClient, state: ScenarioState, number: int, title: str) -> None:
    state.remoteok += [
        {
            "title": title,
            "company": f"Company {index}",
            "description": "Python services.",
            "url": f"https://remoteok.com/more/{index}",
        }
        for index in range(number)
    ]
    _import(client, state)


@given(
    parsers.parse('the job board "Remote OK" was imported again without the offer of "{company}"')
)
def given_imported_again(client: TestClient, state: ScenarioState, company: str) -> None:
    state.remoteok = [row for row in state.remoteok if row["company"] != company]
    _import(client, state)


@given(parsers.parse('an offer for "{company}" as "{title}"'))
def given_offer(client: TestClient, company: str, title: str) -> None:
    body = {"url": "https://jobs.example/hand", "company": company, "title": title}
    _ok(client.post(OFFERS_URL, json=body))


@given(
    parsers.re(
        r'I discarded the offer of "(?P<company>[^"]+)"(?: because "(?P<reason>[^"]+)")?'
        r'(?: with the word "(?P<word>[^"]+)")?$'
    )
)
def given_discarded(client: TestClient, company: str, reason: str | None, word: str | None) -> None:
    body = {} if reason is None else {"reason": reason}
    if word is not None:
        body["word"] = word
    _ok(client.post(f"{_offer_url(client, company)}/discard", json=body))


@given(parsers.parse('I promoted an imported offer as "{title}"'))
def given_promoted_imported(client: TestClient, state: ScenarioState, title: str) -> None:
    url = f"https://remoteok.com/promoted/{len(state.remoteok)}"
    state.remoteok = [
        *state.remoteok,
        {"title": title, "company": "Promoted Co", "description": "Python.", "url": url},
    ]
    _import(client, state)
    _ok(client.post(f"{_offer_url(client, 'Promoted Co')}/promotion", json={}))


@given(parsers.parse('the profile "{name}" has the keywords "{word}"'))
def given_keywords(client: TestClient, name: str, word: str) -> None:
    profile_id = _profile(client, name)["id"]
    _ok(client.patch(f"{PROFILES_URL}/{profile_id}", json={"keywords": [word]}), 200)


@given(parsers.parse('the profile "{name}" excludes "{word}"'))
def given_excludes(client: TestClient, name: str, word: str) -> None:
    profile_id = _profile(client, name)["id"]
    _ok(client.patch(f"{PROFILES_URL}/{profile_id}", json={"excluded_keywords": [word]}), 200)


@given(parsers.parse('I said "Not now" to excluding "{word}" from "{name}"'))
def given_dismissed(client: TestClient, word: str, name: str) -> None:
    body = {"search_profile_id": _profile(client, name)["id"], "word": word}
    _ok(client.post(f"{SUGGESTIONS_URL}/dismissals", json=body))


@given(parsers.parse('no search profile named "{name}"'))
def given_no_profile(client: TestClient, name: str) -> None:
    assert all(p["name"] != name for p in _ok(client.get(PROFILES_URL), 200)["items"])


@given(parsers.parse('I promoted the offer of "{company}"'))
def given_promoted(client: TestClient, company: str) -> None:
    _ok(client.post(f"{_offer_url(client, company)}/promotion", json={}))


@given(
    parsers.re(
        r'the offer triager says the offer of "(?P<company>[^"]+)" is (?P<verdict>OK|KO)'
        r'(?: because "(?P<why>[^"]*)")?'
        r'(?:, with the reason "(?P<reason>[^"]+)" and the evidence "(?P<evidence>[^"]+)")?'
        r'(?:, with the confidence "(?P<confidence>[^"]+)")?'
        r'(?:, quoting "(?P<quote>[^"]+)")?'
        r"(?P<nothing_against>, with nothing against it)?$"
    )
)
def given_answer(  # noqa: PLR0913, PLR0917  # one per part of the step
    state: ScenarioState,
    company: str,
    verdict: str,
    why: str | None,
    reason: str | None,
    evidence: str | None,
    confidence: str | None,
    quote: str | None,
    nothing_against: str | None,  # noqa: ARG001  # an OK has no why not unless told
) -> None:
    state.answers[company] = said(
        verdict, why or "Why.", reason=reason, evidence=evidence, quote=quote
    )
    if confidence is not None:
        state.answers[company] = replace(state.answers[company], confidence=confidence)


@given(
    parsers.re(
        r'the offer triager says of the offer of "(?P<company>[^"]+)": (?P<verdict>OK|KO), '
        r"with (?P<confidence>\w+) confidence$"
    )
)
def given_whys(
    state: ScenarioState, company: str, verdict: str, confidence: str, datatable: list[list[str]]
) -> None:
    sides = {side: (why, quote) for side, why, quote in datatable[1:]}
    yes, quote_yes = sides.get("why yes", (None, None))
    no, quote_not = sides.get("why not", (None, None))
    state.answers[company] = TriageAnswer(
        verdict.lower(), yes, no, quote_yes=quote_yes, quote_not=quote_not, confidence=confidence
    )


@given(
    parsers.parse(
        'the offer triager says the offer of "{company}" is OK with a {side} of {n:d} characters'
    )
)
def given_long_why(state: ScenarioState, company: str, side: str, n: int) -> None:
    long = "w" * n
    yes, no = (long, "No.") if side == "why yes" else ("Yes.", long)
    state.answers[company] = TriageAnswer("ok", yes, no)


@given(parsers.re(r"the offer triager says the offers of (?P<companies>.+) are OK$"))
def given_ok_offers(state: ScenarioState, companies: str) -> None:
    for company in re.findall(r'"([^"]+)"', companies):
        state.answers[company] = TriageAnswer("ok", "Fits.")


@given(
    parsers.re(
        r'the offer triager suggests excluding "(?P<word>[^"]+)" from "(?P<profile>[^"]+)" '
        r'because "(?P<why>[^"]+)", from the offer of "(?P<company>[^"]+)"$'
    )
)
def given_suggests(state: ScenarioState, word: str, profile: str, why: str, company: str) -> None:
    state.suggestions.append((profile, word, why, [company]))


@given(parsers.parse('the offer triager does not answer for the offer of "{company}"'))
def given_unanswered(state: ScenarioState, company: str) -> None:
    state.unanswered.add(company)


@given("the offer triager fails")
def given_failing(state: ScenarioState) -> None:
    state.is_failing = True


@given(parsers.re(r"the offer triager is (?P<triager>Groq|Claude Code(, not installed)?|missing)$"))
def given_triager(state: ScenarioState, triager: str) -> None:
    state.triager = triager


@given("these verdicts:")
def given_verdicts(client: TestClient, state: ScenarioState, datatable: list[list[str]]) -> None:
    # The triager answers for the companies of the table and leaves the others untriaged;
    # a suggested discard comes with valid evidence: a word of the title or the description.
    verdicts = {row["company"]: row for row in _rows(datatable)}
    for offer in state.remoteok:
        row = verdicts.get(offer["company"])
        if row is None:
            state.unanswered.add(offer["company"])
            continue
        reason = row["suggested discard"] or None
        evidence = None
        if reason is not None:
            evidence = offer["title"].split()[0] if reason == "title_word" else offer["description"]
        state.answers[offer["company"]] = said(
            row["verdict"], "Why.", reason=reason, evidence=evidence
        )
    _ok(client.post(TRIAGES_URL))


# --- When ---


@given("I triaged the offers")
@when("I triage the offers")
def when_triage(client: TestClient, state: ScenarioState) -> None:
    state.response = client.post(TRIAGES_URL)


@when(parsers.parse('I accept the suggestion carried by the offer of "{company}"'))
def when_accept(client: TestClient, state: ScenarioState, company: str) -> None:
    offer_id = _offer(client, company)["id"]
    suggestion = next(s for s in _suggestions(client) if offer_id in s["offer_ids"])
    body = {
        "search_profile_id": suggestion["search_profile_id"],
        suggestion["rule"]: suggestion["after"],
        "offer_id": offer_id,
    }
    state.response = client.post("/api/v1/criteria-changes", json=body)


@given("I listed the suggestions")
@when("I list the suggestions")
def when_list(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(SUGGESTIONS_URL)


@when("I check whether the triage is available")
def when_check(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(f"{OFFERS_URL}/triager")


@when("I list the pending offers by verdict")
def when_list_by_verdict(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(
        OFFERS_URL, params={"status": "pending", "by_verdict": "true", "limit": "100"}
    )


# --- Then ---


@then(
    parsers.parse(
        'the offer of "{company}" has a suggested discard because "{reason}" with "{evidence}"'
    )
)
def then_suggested(client: TestClient, company: str, reason: str, evidence: str) -> None:
    expected = {"reason": reason, "evidence": evidence}
    assert _offer(client, company)["suggested_discard"] == expected


@then(parsers.parse('the offer of "{company}" has no suggested discard'))
def then_no_suggestion(client: TestClient, company: str) -> None:
    assert _offer(client, company)["suggested_discard"] is None


@then(parsers.parse('the offer of "{company}" is "{status}"'))
def then_status(client: TestClient, company: str, status: str) -> None:
    assert _offer(client, company)["status"] == status


@then(
    parsers.parse("the triage triaged {triaged:d} offers, failed on {failed:d} and left {left:d}")
)
def then_batch(state: ScenarioState, triaged: int, failed: int, left: int) -> None:
    batch = _ok(state.last_response)
    assert (batch["triaged"], batch["failed"], batch["left"]) == (triaged, failed, left)


@then(parsers.parse("the triage says {ok:d} OK and {ko:d} KO"))
def then_ok_ko(state: ScenarioState, ok: int, ko: int) -> None:
    batch = _ok(state.last_response)
    assert (batch["ok"], batch["ko"]) == (ok, ko)


@then(
    parsers.re(
        r'the offer of "(?P<company>[^"]+)" has the verdict "(?P<verdict>OK|KO)"'
        r'(?: because "(?P<why>[^"]+)")?'
        r"(?: with (?P<confidence>low|medium|high|no) confidence)?$"
    )
)
def then_verdict(
    client: TestClient, company: str, verdict: str, why: str | None, confidence: str | None
) -> None:
    triage = _offer(client, company)["triage"]
    assert triage is not None
    assert triage["verdict"] == verdict.lower()
    if why is not None:
        side = "why_yes" if verdict == "OK" else "why_not"
        assert triage[side]["why"] == why
    if confidence is not None:
        assert triage["confidence"] == (None if confidence == "no" else confidence)


@then(parsers.parse('the offer of "{company}" has these whys:'))
def then_whys(client: TestClient, company: str, datatable: list[list[str]]) -> None:
    triage = _offer(client, company)["triage"]
    shown = [
        [side, triage[key]["why"], triage[key]["quote"] or ""]
        for side, key in (("why yes", "why_yes"), ("why not", "why_not"))
        if triage[key] is not None
    ]
    assert shown == datatable[1:]


@then(parsers.parse('the offer of "{company}" has no why not'))
def then_no_why_not(client: TestClient, company: str) -> None:
    assert _offer(client, company)["triage"]["why_not"] is None


@then(
    parsers.re(
        r'the offer of "(?P<company>[^"]+)" has the why yes "(?P<why>[^"]+)" '
        r'(?:quoting "(?P<quote>[^"]+)"|with no quote)$'
    )
)
def then_why_yes(client: TestClient, company: str, why: str, quote: str | None) -> None:
    assert _offer(client, company)["triage"]["why_yes"] == {"why": why, "quote": quote}


@then(parsers.parse('the offer of "{company}" has a {side} of {n:d} characters'))
def then_why_length(client: TestClient, company: str, side: str, n: int) -> None:
    key = side.replace(" ", "_")
    assert len(_offer(client, company)["triage"][key]["why"]) == n


@then(parsers.parse('the offer of "{company}" has no verdict'))
def then_no_verdict(client: TestClient, company: str) -> None:
    assert _offer(client, company)["triage"] is None


@then(
    parsers.parse(
        'the criteria suggestions include excluding "{word}" from "{profile}", from the '
        'triager because "{why}"'
    ),
    target_fixture="suggestion",
)
def then_includes(client: TestClient, word: str, profile: str, why: str) -> dict[str, Any]:
    suggestion = _suggestion(client, word, profile)
    assert suggestion is not None, _suggestions(client)
    assert (suggestion["source"], suggestion["why"]) == ("triager", why)
    return suggestion


@then(parsers.parse('the criteria suggestions do not include excluding "{word}" from "{profile}"'))
def then_not_includes(client: TestClient, word: str, profile: str) -> None:
    assert _suggestion(client, word, profile) is None


@then(parsers.parse('it comes from the offer of "{company}"'))
def then_comes_from(client: TestClient, suggestion: dict[str, Any], company: str) -> None:
    assert suggestion["offer_ids"] == [_offer(client, company)["id"]]


@then(
    parsers.parse(
        'the offer of "{company}" carries the suggestion to exclude "{word}" from "{profile}"'
    )
)
def then_carries(client: TestClient, company: str, word: str, profile: str) -> None:
    suggestion = _suggestion(client, word, profile)
    assert suggestion is not None
    assert _offer(client, company)["id"] in suggestion["offer_ids"]


@then(parsers.parse('the profile "{name}" has the excluded_keywords "{words}"'))
def then_excluded(client: TestClient, name: str, words: str) -> None:
    assert _profile(client, name)["excluded_keywords"] == re.split(r"\s*,\s*", words)


@then(parsers.parse('the latest change came from the offer of "{company}"'))
def then_change_from(client: TestClient, company: str) -> None:
    changes = _ok(client.get("/api/v1/criteria-changes"), 200)["items"]
    assert changes[0]["offer_id"] == _offer(client, company)["id"]


@then(parsers.re(r"the offer triager was asked once, only about the offers of (?P<companies>.+)$"))
def then_asked(state: ScenarioState, companies: str) -> None:
    offers, _ = state.last_request
    expected = sorted(re.findall(r'"([^"]+)"', companies))
    assert (len(state.requests), sorted(offer.company for offer in offers)) == (1, expected)


@then(parsers.parse('the offer triager was told the profile "{name}" and these decisions:'))
def then_told_decisions(state: ScenarioState, name: str, datatable: list[list[str]]) -> None:
    _, context = state.last_request
    told = sorted(
        (d.title, str(d.status), str(d.reason or ""), d.word or "") for d in context.decisions
    )
    expected = sorted(
        (row["title"], row["decision"], row["reason"], row["word"]) for row in _rows(datatable)
    )
    assert ([terms.name for terms in context.profiles], told) == ([name], expected)


@then("the offer triager was told these mistakes:")
def then_told_mistakes(state: ScenarioState, datatable: list[list[str]]) -> None:
    _, context = state.last_request
    told = sorted(
        (m.title, str(m.mistake).replace("_", " "), str(m.reason or "")) for m in context.mistakes
    )
    expected = sorted((row["title"], row["mistake"], row["reason"]) for row in _rows(datatable))
    assert told == expected


@then(parsers.re(r"it is (?P<availability>available|not available)$"))
def then_available(state: ScenarioState, availability: str) -> None:
    assert _ok(state.last_response, 200) == {"is_available": availability == "available"}


@then("it is rejected because the offer triager is not available")
def then_unavailable(state: ScenarioState) -> None:
    assert state.last_response.status_code == 503, state.last_response.text
    assert state.last_response.json()["type"] == "/problems/offer-triager-unavailable"


@then(parsers.re(r"the offers are, by company: (?P<companies>.+)$"))
def then_offers_by_company(state: ScenarioState, companies: str) -> None:
    items = _ok(state.last_response, 200)["items"]
    assert [o["company"] for o in items] == re.findall(r'"([^"]+)"', companies)
