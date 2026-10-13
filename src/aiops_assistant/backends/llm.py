"""Shared JSON parsing for LLM backends. A reply that is not valid JSON in our schema becomes a failed brief."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from ..models import CATEGORIES, Brief, Claim


def _claim(v: Any) -> Any:
    if isinstance(v, str):
        return {"text": v, "cites": []}
    return v


def parse_brief(raw: str, backend: str) -> Brief:
    text = raw.strip()
    m = re.search(r"\{.*\}", text, flags=re.S)
    try:
        data = json.loads(m.group(0) if m else text)
        data["summary"] = _claim(data.get("summary"))
        data["root_cause"] = _claim(data.get("root_cause"))
        data["next_checks"] = [_claim(c) for c in data.get("next_checks") or []]
        data["category"] = str(data.get("category", "unknown")).strip()
        brief = Brief.model_validate({**data, "backend": backend})
    except (json.JSONDecodeError, ValidationError, TypeError, AttributeError) as e:
        return failed(backend, f"{type(e).__name__}: {str(e)[:200]}")
    if brief.category not in CATEGORIES:
        brief.parse_error = f"category {brief.category!r} not in allowed list"
    return brief


def failed(backend: str, why: str) -> Brief:
    return Brief(
        summary=Claim(text="(no usable answer)"),
        category="unknown",
        root_cause=Claim(text="(none)"),
        backend=backend,
        parse_error=why,
    )
