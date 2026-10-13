"""Data model shared by loader, backends, grounding checks and eval."""

from __future__ import annotations

from pydantic import BaseModel, Field

CATEGORIES: dict[str, str] = {
    "db_pool_exhaustion": "Database connection pool exhausted",
    "cert_expiry": "Expired or invalid TLS certificate",
    "bad_deploy": "Regression introduced by a deployment",
    "dns_failure": "DNS resolution failures",
    "disk_full": "Disk or volume out of space",
    "kafka_consumer_lag": "Kafka consumer lag / stalled consumers",
    "oom_kill": "Memory leak leading to OOMKilled containers",
    "dependency_timeout": "Slow downstream dependency causing timeouts",
    "upstream_rate_limit": "Upstream API rate limiting (HTTP 429)",
    "credential_rotation": "Credential rotated without the consumer being updated",
    "unknown": "Not enough evidence to name a root cause",
}


class LogLine(BaseModel):
    id: str  # "L<n>", 1-based line number in logs.log
    ts: str
    level: str
    service: str
    message: str

    def render(self) -> str:
        return f"{self.ts} {self.level} {self.service} {self.message}"


class Alert(BaseModel):
    id: str  # "A<n>"
    ts: str
    name: str
    service: str
    severity: str
    summary: str


class Label(BaseModel):
    category: str
    root_cause: str
    key_lines: list[str] = Field(default_factory=list)


class Incident(BaseModel):
    id: str
    title: str
    logs: list[LogLine]
    alerts: list[Alert]
    label: Label | None = None

    @property
    def services(self) -> set[str]:
        return {line.service for line in self.logs} | {a.service for a in self.alerts}


class RunbookSection(BaseModel):
    id: str  # "RB:<runbook>#<section-slug>"
    runbook: str
    category: str
    heading: str
    text: str


class Claim(BaseModel):
    text: str
    cites: list[str] = Field(default_factory=list)


class TimelineEntry(BaseModel):
    ts: str
    event: str
    cites: list[str] = Field(default_factory=list)


class Brief(BaseModel):
    """What a backend returns. Every claim must cite evidence ids it was given."""

    summary: Claim
    category: str
    root_cause: Claim
    timeline: list[TimelineEntry] = Field(default_factory=list)
    next_checks: list[Claim] = Field(default_factory=list)
    confidence: str = "low"  # low | medium | high
    backend: str = ""
    parse_error: str | None = None

    def all_claims(self) -> list[Claim]:
        claims = [self.summary, self.root_cause, *self.next_checks]
        claims += [Claim(text=t.event, cites=t.cites) for t in self.timeline]
        return claims
