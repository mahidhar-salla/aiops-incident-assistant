import json

import pytest

from aiops_assistant.backends import get_backend
from aiops_assistant.backends.llm import parse_brief
from aiops_assistant.backends.ollama import OllamaBackend
from aiops_assistant.evidence import build_pack
from aiops_assistant.grounding import check
from aiops_assistant.loader import load_incident


def test_mock_is_deterministic(root, sections):
    inc = load_incident(root / "incidents/inc-005-disk-full")
    pack = build_pack(inc, sections)
    a, b = get_backend("mock").draft(pack), get_backend("mock").draft(pack)
    assert a == b and a.category == "disk_full"


def test_mock_refuses_thin_evidence(root, sections):
    inc = load_incident(root / "incidents/inc-011-noise-only")
    brief = get_backend("mock").draft(build_pack(inc, sections))
    assert brief.category == "unknown" and brief.confidence == "low"


def test_unknown_backend():
    with pytest.raises(ValueError):
        get_backend("gpt-on-a-stick")


def test_parse_brief_accepts_fenced_json_and_string_claims():
    raw = (
        "```json\n"
        + json.dumps({"summary": "x", "category": "disk_full", "root_cause": {"text": "y", "cites": ["L1"]}})
        + "\n```"
    )
    b = parse_brief(raw, "t")
    assert b.parse_error is None and b.summary.text == "x" and b.root_cause.cites == ["L1"]


def test_parse_brief_rejects_garbage_and_bad_category():
    assert parse_brief("I think it was DNS", "t").parse_error
    assert parse_brief(json.dumps({"summary": "x", "category": "aliens", "root_cause": "y"}), "t").parse_error


def test_ollama_backend_uses_http_and_grounding_catches_fake_cites(root, sections, monkeypatch):
    inc = load_incident(root / "incidents/inc-004-dns")
    pack = build_pack(inc, sections)
    fake = {
        "summary": {"text": "DNS lookups for ledger.internal time out", "cites": [pack.logs[0].id]},
        "category": "dns_failure",
        "root_cause": {"text": "coredns upstream down since 9999 on payments-mesh-x", "cites": ["L999", "A1"]},
        "timeline": [{"ts": "2030-01-01T00:00:00Z", "event": "made up", "cites": ["A1"]}],
        "next_checks": [],
        "confidence": "high",
    }
    be = OllamaBackend(model="test")
    monkeypatch.setattr(be, "complete", lambda prompt: json.dumps(fake))
    brief = be.draft(pack)
    g = check(brief, pack, inc)
    assert brief.category == "dns_failure"
    assert g.invalid_cites == ["L999"]
    assert "9999" in g.unsupported_numbers and "payments-mesh-x" in g.unsupported_identifiers
    assert g.bad_timestamps == ["2030-01-01T00:00:00Z"]
    assert not g.hallucination_free


def test_ollama_unreachable_is_a_failed_brief(root, sections):
    inc = load_incident(root / "incidents/inc-004-dns")
    be = OllamaBackend(model="x", host="http://127.0.0.1:9", timeout=1)
    assert be.draft(build_pack(inc, sections)).parse_error


def test_bedrock_without_boto3_or_creds_fails_cleanly(root, sections, monkeypatch):
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    for k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_PROFILE"):
        monkeypatch.delenv(k, raising=False)
    inc = load_incident(root / "incidents/inc-004-dns")
    brief = get_backend("bedrock").draft(build_pack(inc, sections))
    assert brief.parse_error and brief.category == "unknown"
