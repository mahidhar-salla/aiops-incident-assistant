"""Build the evidence pack a backend sees: redacted log lines, alerts and retrieved runbook sections.

Every item has a stable id (L<n>, A<n>, RB:<runbook>#<section>) that the model must cite.
"""

from __future__ import annotations

from pydantic import BaseModel

from .models import Alert, Incident, LogLine, RunbookSection
from .redact import redact
from .retrieval import search

SIGNAL_LEVELS = {"WARN", "ERROR", "FATAL"}


class EvidencePack(BaseModel):
    incident_id: str
    title: str
    logs: list[LogLine]
    alerts: list[Alert]
    runbooks: list[RunbookSection]
    runbook_scores: dict[str, float]
    redactions: dict[str, int]
    total_log_lines: int

    def ids(self) -> set[str]:
        return {x.id for x in self.logs} | {a.id for a in self.alerts} | {r.id for r in self.runbooks}

    def query(self) -> str:
        return " ".join([*(line.message for line in self.logs), *(f"{a.name} {a.summary}" for a in self.alerts)])


def build_pack(incident: Incident, sections: list[RunbookSection], max_lines: int = 40, k: int = 4) -> EvidencePack:
    counts: dict[str, int] = {}
    clean: list[LogLine] = []
    for line in incident.logs:
        msg, c = redact(line.message)
        for key, v in c.items():
            counts[key] = counts.get(key, 0) + v
        clean.append(line.model_copy(update={"message": msg}))
    # Keep every WARN/ERROR line plus INFO lines that mention change events; drop routine noise.
    change_words = ("rollout", "deploy", "rotated", "re-run", "rebalanc", "restart", "back-off")
    signal = [x for x in clean if x.level in SIGNAL_LEVELS or any(w in x.message.lower() for w in change_words)]
    signal = signal[:max_lines]
    query = " ".join([*(x.message for x in signal), *(f"{a.name} {a.summary}" for a in incident.alerts)])
    hits = search(sections, query, k=k)
    return EvidencePack(
        incident_id=incident.id,
        title=incident.title,
        logs=signal,
        alerts=incident.alerts,
        runbooks=[s for s, _ in hits],
        runbook_scores={s.id: round(v, 3) for s, v in hits},
        redactions=counts,
        total_log_lines=len(incident.logs),
    )
