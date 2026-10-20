import pytest

from aiops_assistant.evidence import EvidencePack
from aiops_assistant.grounding import check
from aiops_assistant.models import Brief, Claim, Incident, LogLine


def _numbers(evidence: str, claim: str) -> list[str]:
    line = LogLine(id="L1", ts="2026-10-20T10:00:00Z", level="ERROR", service="checkout-api", message=evidence)
    inc = Incident(id="inc-x", title="t", logs=[line], alerts=[])
    pack = EvidencePack(
        incident_id="inc-x",
        title="t",
        logs=[line],
        alerts=[],
        runbooks=[],
        runbook_scores={},
        redactions={},
        total_log_lines=1,
    )
    brief = Brief(summary=Claim(text=claim, cites=["L1"]), category="unknown", root_cause=Claim(text="x", cites=["L1"]))
    return check(brief, pack, inc).unsupported_numbers


@pytest.mark.parametrize(
    "evidence",
    [
        "upstream timeout after 30000ms",  # 300 is only a prefix of a bigger number
        "pool size 1300 reached",  # ...or a suffix
        "p99 latency 300.5 ms",  # ...or the integer part of a decimal
        "request id abc300 failed",  # ...or part of an id
    ],
)
def test_number_inside_a_bigger_token_is_not_grounded(evidence):
    assert _numbers(evidence, "timeouts started at 300 ms") == ["300"]


@pytest.mark.parametrize(
    ("evidence", "claim"),
    [
        ("upstream timeout after 300 ms", "timeouts started at 300 ms"),
        ("upstream timeout after 300ms", "timeouts started at 300 ms"),  # a unit attached to the number is fine
        ("retry budget=300, giving up", "gave up after a budget of 300"),
        ("latency 300.5 ms over budget", "latency hit 300.5 ms"),  # a decimal grounds itself
    ],
)
def test_number_as_its_own_token_is_grounded(evidence, claim):
    assert _numbers(evidence, claim) == []
