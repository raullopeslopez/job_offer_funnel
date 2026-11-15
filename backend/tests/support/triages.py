from funnel.modules.inbox.domain import TriageAnswer


def said(
    verdict: str,
    why: str,
    *,
    reason: str | None = None,
    evidence: str | None = None,
    quote: str | None = None,
) -> TriageAnswer:
    """What the triager says, as the specs put it: an offer OK "because" something has that
    why yes, and one KO "because" something has that why not."""
    if verdict.lower() == "ok":
        return TriageAnswer("ok", why, reason=reason, evidence=evidence, quote_yes=quote)
    return TriageAnswer("ko", why_not=why, reason=reason, evidence=evidence, quote_not=quote)
