"""The prompt sent to LLM backends. Kept in one place so it is easy to review."""

from __future__ import annotations

from .evidence import EvidencePack
from .models import CATEGORIES

SYSTEM = """You are assisting an on-call site reliability engineer. You draft; a human decides.
Rules:
- Use ONLY the evidence provided. Every claim must cite evidence ids exactly as given
  (e.g. "L12", "A1", "RB:disk-full#checks").
- Never invent log lines, ids, services, numbers or timestamps.
- Do not recommend running commands automatically. Suggest checks for a human.
- If the evidence does not support a root cause, use category "unknown" and confidence "low".
Respond with a single JSON object and nothing else."""

SCHEMA = """{
  "summary": {"text": "...", "cites": ["L.."]},
  "category": "<one of the allowed categories>",
  "root_cause": {"text": "...", "cites": ["L..", "RB:..."]},
  "timeline": [{"ts": "<timestamp from evidence>", "event": "...", "cites": ["L.."]}],
  "next_checks": [{"text": "...", "cites": ["RB:..."]}],
  "confidence": "low|medium|high"
}"""


def render(pack: EvidencePack) -> str:
    cats = "\n".join(f"- {k}: {v}" for k, v in CATEGORIES.items())
    logs = "\n".join(f"[{x.id}] {x.render()}" for x in pack.logs)
    alerts = "\n".join(f"[{a.id}] {a.ts} {a.severity} {a.name} service={a.service}: {a.summary}" for a in pack.alerts)
    rbs = "\n".join(f"[{r.id}] ({r.category}) {r.heading}: {r.text}" for r in pack.runbooks)
    return (
        f"Incident: {pack.title}\n\nAllowed categories:\n{cats}\n\n"
        f"Alerts:\n{alerts or '(none)'}\n\nLog lines (redacted, WARN/ERROR and change events):\n{logs or '(none)'}\n\n"
        f"Runbook sections:\n{rbs or '(none)'}\n\nReturn JSON with this shape:\n{SCHEMA}"
    )
