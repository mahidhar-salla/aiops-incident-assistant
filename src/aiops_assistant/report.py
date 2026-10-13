"""Render a brief as Markdown for the on-call engineer (and the incident ticket)."""

from __future__ import annotations

from .evidence import EvidencePack
from .grounding import GroundingReport
from .models import CATEGORIES, Brief, Claim


def _c(claim: Claim) -> str:
    cites = " ".join(f"`{c}`" for c in claim.cites) or "**(uncited)**"
    return f"{claim.text} [{cites}]"


def to_markdown(brief: Brief, pack: EvidencePack, g: GroundingReport) -> str:
    out = [
        f"# Incident brief (DRAFT): {pack.title}",
        "",
        f"> Drafted by `{brief.backend}` from {len(pack.logs)} of {pack.total_log_lines} log lines and "
        f"{len(pack.alerts)} alerts after redaction ({sum(pack.redactions.values())} items scrubbed). "
        "**A human must review this before it is shared or acted on.** No actions were taken.",
        "",
        f"**Suspected category:** {CATEGORIES.get(brief.category, brief.category)} (confidence: {brief.confidence})",
        "",
        f"**Summary:** {_c(brief.summary)}",
        "",
        f"**Likely root cause:** {_c(brief.root_cause)}",
        "",
        "## Timeline (UTC)",
        *(f"- {t.ts} {t.event} [{' '.join(f'`{c}`' for c in t.cites)}]" for t in brief.timeline),
        "",
        "## What to check next",
        *(f"- {_c(c)}" for c in brief.next_checks),
        "",
        "## Grounding check",
        f"- Citations valid: {g.total_cites - len(g.invalid_cites)}/{g.total_cites}"
        + (f" (invalid: {', '.join(g.invalid_cites)})" if g.invalid_cites else ""),
        f"- Uncited claims: {g.uncited_claims}",
        f"- Unsupported numbers/identifiers: {len(g.unsupported_numbers) + len(g.unsupported_identifiers)}",
        f"- Result: {'PASS' if g.hallucination_free else 'FAIL: do not trust without checking the sources'}",
        "",
        "## Cited evidence",
    ]
    cited = {c for claim in brief.all_claims() for c in claim.cites}
    for x in pack.logs:
        if x.id in cited:
            out.append(f"- `{x.id}` `{x.render()}`")
    for a in pack.alerts:
        if a.id in cited:
            out.append(f"- `{a.id}` alert {a.name} ({a.severity}) at {a.ts}: {a.summary}")
    for r in pack.runbooks:
        if r.id in cited:
            out.append(f'- `{r.id}` runbooks/{r.runbook}.md, section "{r.heading}"')
    if brief.parse_error:
        out += ["", f"> Backend output problem: {brief.parse_error}"]
    return "\n".join(out) + "\n"
