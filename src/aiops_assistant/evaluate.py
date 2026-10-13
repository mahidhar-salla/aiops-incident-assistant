"""Score briefs against labelled synthetic incidents."""

from __future__ import annotations

import time
from pathlib import Path

from pydantic import BaseModel

from .backends import Backend
from .evidence import build_pack
from .grounding import GroundingReport, check
from .loader import incident_dirs, load_incident
from .models import Brief, RunbookSection


class CaseResult(BaseModel):
    incident: str
    expected: str
    got: str
    root_cause_match: bool
    key_evidence_cited: bool
    citation_validity: float
    hallucination_free: bool
    uncited_claims: int
    parse_error: str | None
    seconds: float
    grounding: GroundingReport
    brief: Brief


class EvalSummary(BaseModel):
    backend: str
    n: int
    root_cause_accuracy: float
    key_evidence_rate: float
    citation_validity: float
    hallucination_free_rate: float
    parse_failures: int
    mean_seconds: float
    cases: list[CaseResult]


def run_eval(backend: Backend, incidents_root: Path, sections: list[RunbookSection]) -> EvalSummary:
    cases: list[CaseResult] = []
    for d in incident_dirs(incidents_root):
        inc = load_incident(d, with_label=True)
        assert inc.label is not None, f"{d} has no label.yaml"
        pack = build_pack(inc, sections)
        t0 = time.perf_counter()
        brief = backend.draft(pack)
        dt = time.perf_counter() - t0
        g = check(brief, pack, inc)
        cited = {c for claim in brief.all_claims() for c in claim.cites}
        key_ok = bool(cited & set(inc.label.key_lines)) if inc.label.key_lines else brief.category == "unknown"
        cases.append(
            CaseResult(
                incident=inc.id,
                expected=inc.label.category,
                got=brief.category,
                root_cause_match=brief.category == inc.label.category,
                key_evidence_cited=key_ok,
                citation_validity=round(g.citation_validity, 3),
                hallucination_free=g.hallucination_free,
                uncited_claims=g.uncited_claims,
                parse_error=brief.parse_error,
                seconds=round(dt, 2),
                grounding=g,
                brief=brief,
            )
        )
    n = len(cases) or 1
    return EvalSummary(
        backend=backend.name,
        n=len(cases),
        root_cause_accuracy=round(sum(c.root_cause_match for c in cases) / n, 3),
        key_evidence_rate=round(sum(c.key_evidence_cited for c in cases) / n, 3),
        citation_validity=round(sum(c.citation_validity for c in cases) / n, 3),
        hallucination_free_rate=round(sum(c.hallucination_free for c in cases) / n, 3),
        parse_failures=sum(c.parse_error is not None for c in cases),
        mean_seconds=round(sum(c.seconds for c in cases) / n, 2),
        cases=cases,
    )
