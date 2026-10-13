"""Deterministic offline backend: retrieval + rules, no model, no network.

This is a baseline, not an LLM. It exists so tests, CI and the demo run with no keys, and so the eval
has something to compare real models against.
"""

from __future__ import annotations

from collections import defaultdict

from ..evidence import EvidencePack
from ..models import CATEGORIES, Brief, Claim, TimelineEntry
from ..retrieval import BM25

CHANGE_WORDS = ("rollout", "deploy", "rotated", "re-run", "rebalanc")


class MockBackend:
    name = "mock"

    def draft(self, pack: EvidencePack) -> Brief:
        errors = [x for x in pack.logs if x.level in {"ERROR", "FATAL"}]
        pages = [a for a in pack.alerts if a.severity == "page"]
        if not pack.runbooks or (not errors and not pages):
            cites = [x.id for x in pack.logs[:2]] + [a.id for a in pack.alerts[:1]]
            return Brief(
                summary=Claim(text=f"{pack.title}: no ERROR lines and no paging alert in the evidence.", cites=cites),
                category="unknown",
                root_cause=Claim(text="Not enough evidence to name a root cause.", cites=cites),
                next_checks=[Claim(text="Confirm whether the alert is still firing before escalating.", cites=cites)],
                confidence="low",
                backend=self.name,
            )
        by_cat: dict[str, float] = defaultdict(float)
        for rb in pack.runbooks:
            by_cat[rb.category] += pack.runbook_scores.get(rb.id, 0.0)
        category = max(by_cat, key=lambda c: by_cat[c])
        best = [rb for rb in pack.runbooks if rb.category == category]
        # Pick the log lines that look most like the chosen runbook.
        scores = BM25([x.message for x in pack.logs]).score(" ".join(rb.text for rb in best))
        ranked = [x for x, s in sorted(zip(pack.logs, scores, strict=True), key=lambda p: -p[1]) if s > 0]
        top = ranked[:3] or errors[:3]
        top_ids = [x.id for x in top]
        services = sorted({x.service for x in top})
        share = by_cat[category] / max(sum(by_cat.values()), 1e-9)
        confidence = "high" if share > 0.75 else "medium" if share > 0.5 else "low"

        timeline: list[TimelineEntry] = []
        firsts = [
            next((x for x in pack.logs if any(w in x.message.lower() for w in CHANGE_WORDS)), None),
            next((x for x in pack.logs if x.level == "WARN"), None),
            errors[0] if errors else None,
        ]
        for x in firsts:
            if x is not None and x.id not in {c for t in timeline for c in t.cites}:
                timeline.append(TimelineEntry(ts=x.ts, event=f"{x.service}: {x.message[:110]}", cites=[x.id]))
        for a in pack.alerts:
            timeline.append(TimelineEntry(ts=a.ts, event=f"Alert {a.name} ({a.severity}) on {a.service}", cites=[a.id]))
        timeline.sort(key=lambda t: t.ts)

        checks_rb = next((rb for rb in best if rb.heading.lower() == "checks"), best[0])
        checks = [s.strip() + "." for s in checks_rb.text.split(".") if s.strip()][:3]
        return Brief(
            summary=Claim(
                text=f"{pack.title}. Errors concentrated in {', '.join(services)}; pattern matches "
                f"'{CATEGORIES[category].lower()}'.",
                cites=top_ids,
            ),
            category=category,
            root_cause=Claim(
                text=f"Likely {CATEGORIES[category].lower()}. Strongest evidence: {top[0].message[:140]}",
                cites=[*top_ids, best[0].id],
            ),
            timeline=timeline,
            next_checks=[Claim(text=c, cites=[checks_rb.id]) for c in checks],
            confidence=confidence,
            backend=self.name,
        )
