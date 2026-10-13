"""Runbook loading and a small BM25 index. No embeddings, so it runs anywhere and is easy to inspect."""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

import yaml

from .models import RunbookSection

_TOKEN = re.compile(r"[a-z][a-z0-9_.]+")
_STOP = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "are",
    "was",
    "not",
    "only",
    "into",
    "its",
    "then",
    "after",
    "before",
    "over",
    "than",
    "when",
    "such",
    "per",
    "all",
    "can",
    "has",
    "have",
    "one",
}


def tokens(text: str) -> list[str]:
    return [t.strip(".") for t in _TOKEN.findall(text.lower()) if t.strip(".") not in _STOP and len(t) > 2]


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def load_runbooks(root: Path) -> list[RunbookSection]:
    sections: list[RunbookSection] = []
    for path in sorted(root.glob("*.md")):
        _, front, body = path.read_text().split("---", 2)
        meta = yaml.safe_load(front)
        for chunk in re.split(r"^## ", body, flags=re.M)[1:]:
            heading, _, text = chunk.partition("\n")
            sections.append(
                RunbookSection(
                    id=f"RB:{path.stem}#{slug(heading)}",
                    runbook=path.stem,
                    category=meta["category"],
                    heading=heading.strip(),
                    text=" ".join(text.split()),
                )
            )
    return sections


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.4, b: float = 0.75) -> None:
        self.docs = [Counter(tokens(d)) for d in docs]
        self.lens = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lens) / max(len(self.lens), 1)
        df: Counter[str] = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.k1, self.b = k1, b

    def score(self, query: str) -> list[float]:
        q = tokens(query)
        out = []
        for d, length in zip(self.docs, self.lens, strict=True):
            s = 0.0
            for t in q:
                f = d.get(t, 0)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * length / self.avg))
            out.append(s)
        return out


def search(sections: list[RunbookSection], query: str, k: int = 4) -> list[tuple[RunbookSection, float]]:
    scores = BM25([f"{s.heading} {s.text}" for s in sections]).score(query)
    ranked = sorted(zip(sections, scores, strict=True), key=lambda p: -p[1])
    return [p for p in ranked[:k] if p[1] > 0]
