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
    # The key may end a longer name (DB_PASSWORD, refresh_token, aws_secret_access_key, spring.datasource.password);
    # it must be followed by the separator, so names like token_expiry or max_tokens are left alone.
    (
        "SECRET",
        re.compile(
            r"(?i)((?:\b|(?<=[_.-]))"
            r"(?:password|passwd|pwd|secret[_-]?(?:access[_-]?)?key|secret|client[_-]?secret|token|access[_-]?token"
            r"|api[_-]?key)"
            r"[\"']?\s*[:=]\s*(?P<q>[\"'])?)"
            # A quoted value runs to the closing quote (or the end of the line), so spaces, commas and braces inside
            # it are redacted too. An unquoted value stops at whitespace, a quote or a brace, and at a comma or
            # semicolon only when what follows starts the next key (",host=db") or is not part of the value
            # (", retrying"), so password=abc,def is redacted whole.
            r"((?(q)(?:(?!(?P=q))[^\n])+|[^\s\"',;}]+(?:[,;](?=[^\s\"',;}])(?![\w.-]+\s*[:=])[^\s\"',;}]+)*))"
        ),
    ),
    # 13-19 digits, optionally grouped. Only redacted when it starts like a major card network (2-6) and passes
    # Luhn; that keeps epoch-millisecond timestamps (13 digits starting with 1) and other long ids intact.
    ("CARD", re.compile(r"\b\d(?:[ -]?\d){12,18}\b")),
    # North American numbers with separators ("416-555-0199", "(416) 555-0199", "+1 416.555.0199") and compact
    # E.164 ("+14165550199"). Runs before SIN_SSN, which used to swallow 3-3-4 phone numbers under the wrong label.
    (
        "PHONE",
        re.compile(r"(?<![\w+])(?:\+?1[ .-]?)?(?:\(\d{3}\) ?|\d{3}[ .-])\d{3}[ .-]\d{4}\b|(?<![\w+])\+\d{10,14}\b"),
    ),
    ("SIN_SSN", re.compile(r"\b(?:\d{3}-\d{2}-\d{4}|\d{3}-\d{3}-\d{3})\b")),
    # Canadian SINs are often written with spaces ("046 454 286"). Three spaced digit groups are common in
    # ordinary logs, so this form is only redacted when it passes the SIN check digit (Luhn).
    ("SIN_SSN", re.compile(r"\b\d{3} \d{3} \d{3}\b")),
    ("IPV4", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
]


def luhn_ok(digits: str) -> bool:
    """Luhn checksum, used by SINs and payment card numbers."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0


# Infrastructure addresses are useful evidence (e.g. a DNS server); only public-looking client IPs are PII.
_PRIVATE = re.compile(r"^(10\.|127\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)")


def redact(text: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}

    def sub(kind: str) -> Callable[[re.Match[str]], str]:
        def _f(m: re.Match[str]) -> str:
            if kind == "IPV4" and _PRIVATE.match(m.group(0)):
                return m.group(0)
            if kind == "CARD":
                digits = re.sub(r"[ -]", "", m.group(0))
                if digits[0] not in "23456" or not luhn_ok(digits):
                    return m.group(0)
            if kind == "SIN_SSN" and " " in m.group(0) and not luhn_ok(m.group(0).replace(" ", "")):
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
