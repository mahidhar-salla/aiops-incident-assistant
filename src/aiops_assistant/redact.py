"""Scrub PII and secrets from log text before any of it is put in a prompt.

Pattern-based, so it is a safety net, not a guarantee. Treat it as one layer next to
not logging PII in the first place.
"""

from __future__ import annotations

import re
from collections.abc import Callable

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("AWS_KEY", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("BEARER", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}")),
    ("BASIC", re.compile(r"(?i)\b(authorization[\"']?\s*[:=]\s*[\"']?basic)\s+[A-Za-z0-9+/]{4,}={0,2}")),
    # key=value, key: value and JSON "key": "value". Group 1 (key + separator) is kept, the value is replaced.
    (
        "SECRET",
        re.compile(
            r"(?i)(\b(?:password|passwd|pwd|secret|client[_-]?secret|token|access[_-]?token|api[_-]?key)"
            r"[\"']?\s*[:=]\s*[\"']?)([^\s\"',;}]+)"
        ),
    ),
    ("CARD", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    ("SIN_SSN", re.compile(r"\b\d{3}-\d{2,3}-\d{3,4}\b")),
    ("IPV4", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
]

# Infrastructure addresses are useful evidence (e.g. a DNS server); only public-looking client IPs are PII.
_PRIVATE = re.compile(r"^(10\.|127\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)")


def redact(text: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}

    def sub(kind: str) -> Callable[[re.Match[str]], str]:
        def _f(m: re.Match[str]) -> str:
            if kind == "IPV4" and _PRIVATE.match(m.group(0)):
                return m.group(0)
            if kind in ("SECRET", "BASIC"):
                counts[kind] = counts.get(kind, 0) + 1
                return f"{m.group(1)} [REDACTED]" if kind == "BASIC" else f"{m.group(1)}[REDACTED]"
            counts[kind] = counts.get(kind, 0) + 1
            return f"[{kind}]"

        return _f

    for kind, pat in PATTERNS:
        text = pat.sub(sub(kind), text)
    return text, counts
