"""Hallucination checks. A brief passes only if everything it points at is really there."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from .evidence import EvidencePack
from .models import Brief, Incident

_NUM = re.compile(r"\b\d{3,}(?:\.\d+)?\b")
_IDENT = re.compile(r"\b[a-z][a-z0-9]*(?:-[a-z0-9]+){1,3}\b")
_TS = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


class GroundingReport(BaseModel):
    total_cites: int = 0
    invalid_cites: list[str] = Field(default_factory=list)  # ids not in the evidence pack or the source
    uncited_claims: int = 0
    unsupported_numbers: list[str] = Field(default_factory=list)
    unsupported_identifiers: list[str] = Field(default_factory=list)
    bad_timestamps: list[str] = Field(default_factory=list)

    @property
    def citation_validity(self) -> float:
        return 1.0 if self.total_cites == 0 else 1 - len(self.invalid_cites) / self.total_cites

    @property
    def hallucination_free(self) -> bool:
        return not (
            self.invalid_cites or self.unsupported_numbers or self.unsupported_identifiers or self.bad_timestamps
        )


def check(brief: Brief, pack: EvidencePack, incident: Incident) -> GroundingReport:
    rep = GroundingReport()
    source_ids = {x.id for x in incident.logs} | {a.id for a in incident.alerts}
    pack_ids = pack.ids()
    corpus = "\n".join(
        [
            pack.title,
            *(x.render() for x in pack.logs),
            *(f"{a.ts} {a.name} {a.service} {a.severity} {a.summary}" for a in pack.alerts),
            *(f"{r.runbook} {r.heading} {r.text}" for r in pack.runbooks),
        ]
    ).lower()
    for claim in brief.all_claims():
        if not claim.cites:
            rep.uncited_claims += 1
        for cid in claim.cites:
            rep.total_cites += 1
            in_source = cid in source_ids or cid.startswith("RB:")
            if cid not in pack_ids or not in_source:
                rep.invalid_cites.append(cid)
        low = claim.text.lower()
        rep.unsupported_numbers += [n for n in _NUM.findall(low) if n not in corpus]
        rep.unsupported_identifiers += [i for i in _IDENT.findall(low) if i not in corpus]
    stamps = set(_TS.findall(corpus.upper()))
    rep.bad_timestamps = [t.ts for t in brief.timeline if t.ts not in stamps]
    return rep
