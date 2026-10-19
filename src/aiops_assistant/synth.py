"""Deterministic generator for the labelled synthetic incidents under incidents/.

Everything here is invented: service names, hosts, users and numbers. Some noise lines carry
fake PII (emails, IPs, card-like numbers) on purpose so the redaction step has something to do.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from .redact import luhn_ok

# (offset seconds from start, level, service, message, is_key_evidence)
Event = tuple[int, str, str, str, bool]
# (offset seconds, alert name, service, severity, summary)
AlertSpec = tuple[int, str, str, str, str]

NOISE = [
    "GET /healthz 200 2ms",
    "request completed status=200 path=/v1/{svc} duration_ms={ms}",
    "cache hit ratio=0.{r}",
    "user login ok email={email} src_ip={ip}",
    "payment authorised card={card} amount=42.10 status=ok",
    "scheduled job heartbeat ok",
    "GC pause young 8ms",
]
NAMES = ["alex", "sam", "priya", "jordan", "li", "maria", "omar", "chen"]


@dataclass
class Scenario:
    id: str
    title: str
    category: str
    root_cause: str
    services: list[str]
    events: list[Event]
    alerts: list[AlertSpec]
    start: str = "2026-09-14T02:00:00Z"
    noise_lines: int = 40
    extra: dict[str, str] = field(default_factory=dict)


SCENARIOS: list[Scenario] = [
    Scenario(
        "inc-001-db-pool",
        "Orders API latency and 5xx",
        "db_pool_exhaustion",
        "orders-api exhausted its database connection pool (max 50); requests queued then timed out.",
        ["orders-api", "checkout-web", "postgres-orders"],
        [
            (300, "WARN", "orders-api", "HikariPool-1 - pool stats total=50 active=50 idle=0 waiting=37", True),
            (
                330,
                "ERROR",
                "orders-api",
                "HikariPool-1 - Connection is not available, request timed out after 30000ms",
                True,
            ),
            (335, "ERROR", "checkout-web", "upstream orders-api returned 503 after 30012ms path=/v1/orders", False),
            (
                360,
                "ERROR",
                "orders-api",
                "SQLTransientConnectionException: connection pool exhausted (waiting=212)",
                True,
            ),
            (400, "WARN", "postgres-orders", "connections in use 50 of max_connections 200 for role orders_app", False),
            (
                420,
                "ERROR",
                "orders-api",
                "HikariPool-1 - Connection is not available, request timed out after 30000ms",
                True,
            ),
        ],
        [
            (345, "OrdersApiHighLatencyP99", "orders-api", "page", "p99 latency above 2s for 5m"),
            (380, "OrdersApiErrorBudgetBurn", "orders-api", "page", "14.4x burn rate on availability SLO"),
        ],
    ),
    Scenario(
        "inc-002-cert-expiry",
        "Partner payments failing with TLS errors",
        "cert_expiry",
        "The client certificate used by payments-gateway for the partner mTLS connection expired at midnight UTC.",
        ["payments-gateway", "partner-proxy"],
        [
            (
                60,
                "ERROR",
                "payments-gateway",
                "x509: certificate has expired or is not yet valid: current time 2026-09-14T02:01:00Z is after 2026-09-14T00:00:00Z",
                True,
            ),
            (
                61,
                "ERROR",
                "partner-proxy",
                "TLS handshake error from payments-gateway: remote error: tls: bad certificate",
                True,
            ),
            (120, "WARN", "payments-gateway", "retrying partner call attempt=3 err=tls handshake failure", False),
            (
                180,
                "ERROR",
                "payments-gateway",
                "x509: certificate has expired or is not yet valid: current time 2026-09-14T02:03:00Z is after 2026-09-14T00:00:00Z",
                True,
            ),
        ],
        [
            (90, "TLSHandshakeFailuresHigh", "partner-proxy", "page", "TLS handshake failure ratio above 50%"),
            (150, "BlackboxProbeFailed", "payments-gateway", "ticket", "probe https://partner.example.test failed"),
        ],
    ),
    Scenario(
        "inc-003-bad-deploy",
        "Accounts API 500s after release",
        "bad_deploy",
        "accounts-api release 2.14.0 removed a default for the currency field; requests without it raise KeyError.",
        ["accounts-api", "deploy-controller", "mobile-bff"],
        [
            (
                100,
                "INFO",
                "deploy-controller",
                "rollout started deployment=accounts-api image=accounts-api:2.14.0 replicas=6",
                True,
            ),
            (160, "INFO", "deploy-controller", "rollout complete deployment=accounts-api revision=41", True),
            (
                175,
                "ERROR",
                "accounts-api",
                "unhandled exception in GET /v1/accounts/summary: KeyError: 'currency' (version=2.14.0)",
                True,
            ),
            (180, "ERROR", "mobile-bff", "accounts-api returned 500 path=/v1/accounts/summary", False),
            (
                200,
                "ERROR",
                "accounts-api",
                "unhandled exception in GET /v1/accounts/summary: KeyError: 'currency' (version=2.14.0)",
                True,
            ),
            (240, "WARN", "accounts-api", "error rate 18% over last 60s (previous revision 40 baseline 0.1%)", True),
        ],
        [(230, "AccountsApi5xxRatioHigh", "accounts-api", "page", "5xx ratio above 5% for 2m")],
    ),
    Scenario(
        "inc-004-dns",
        "Ledger lookups failing across services",
        "dns_failure",
        "Cluster DNS (coredns) could not reach its upstream resolver; lookups of ledger.internal timed out.",
        ["ledger-client", "statements-svc", "coredns"],
        [
            (
                50,
                "ERROR",
                "coredns",
                "[ERROR] plugin/errors: 2 ledger.internal. A: read udp 10.0.4.12:51022->10.0.0.2:53: i/o timeout",
                True,
            ),
            (
                55,
                "ERROR",
                "ledger-client",
                "dial tcp: lookup ledger.internal on 10.96.0.10:53: read udp: i/o timeout",
                True,
            ),
            (
                70,
                "ERROR",
                "statements-svc",
                "dial tcp: lookup ledger.internal on 10.96.0.10:53: no such host (SERVFAIL)",
                True,
            ),
            (90, "WARN", "statements-svc", "request to ledger.internal failed, retrying in 2s", False),
            (130, "ERROR", "coredns", "[ERROR] plugin/forward: no healthy upstreams for zone internal.", True),
        ],
        [
            (100, "CoreDNSForwardHealthcheckFailed", "coredns", "page", "coredns forward upstream unhealthy"),
            (110, "StatementsSvcErrors", "statements-svc", "ticket", "error ratio above 2%"),
        ],
    ),
    Scenario(
        "inc-005-disk-full",
        "Report exports failing",
        "disk_full",
        "The export worker's data volume filled up because rotated temp files were never cleaned up.",
        ["export-worker", "node-exporter"],
        [
            (200, "WARN", "export-worker", "temp dir /var/lib/export/tmp size=46.2GiB files=18211", True),
            (260, "ERROR", "export-worker", "write /var/lib/export/tmp/rpt-8812.csv: no space left on device", True),
            (262, "ERROR", "export-worker", "job rpt-8812 failed: OSError: [Errno 28] No space left on device", True),
            (300, "WARN", "node-exporter", "filesystem /var/lib/export avail=0B (100% used)", True),
        ],
        [
            (240, "NodeFilesystemAlmostOutOfSpace", "node-exporter", "ticket", "/var/lib/export over 95% used"),
            (310, "ExportJobsFailing", "export-worker", "page", "export job failure ratio above 50%"),
        ],
    ),
    Scenario(
        "inc-006-kafka-lag",
        "Notifications delayed by up to 40 minutes",
        "kafka_consumer_lag",
        "notify-consumer took too long per batch, exceeded max.poll.interval.ms and kept rebalancing, so lag grew.",
        ["notify-consumer", "kafka-broker", "notify-api"],
        [
            (
                120,
                "WARN",
                "notify-consumer",
                "consumer poll timeout has expired: time between poll() calls exceeded max.poll.interval.ms=300000",
                True,
            ),
            (
                125,
                "INFO",
                "kafka-broker",
                "group notify-consumers rebalancing: member notify-consumer-3 left (poll timeout)",
                True,
            ),
            (300, "WARN", "notify-consumer", "consumer group notify-consumers lag=184220 on topic notifications", True),
            (420, "WARN", "notify-consumer", "batch of 500 records took 341s to process", True),
            (430, "INFO", "notify-api", "enqueued notification id=n-55120", False),
        ],
        [(320, "KafkaConsumerGroupLagHigh", "notify-consumer", "page", "lag above 100k for 10m")],
    ),
    Scenario(
        "inc-007-oom",
        "Quote service restarting repeatedly",
        "oom_kill",
        "quote-svc leaked memory in an unbounded in-process cache; pods hit the 1GiB limit and were OOMKilled.",
        ["quote-svc", "kubelet"],
        [
            (100, "WARN", "quote-svc", "heap usage 812MiB of 1024MiB limit, cache entries=1940221", True),
            (220, "WARN", "quote-svc", "heap usage 1001MiB of 1024MiB limit, cache entries=2381904", True),
            (
                240,
                "ERROR",
                "kubelet",
                "container quote-svc in pod quote-svc-7d9f exited: OOMKilled (exit code 137)",
                True,
            ),
            (250, "INFO", "kubelet", "Back-off restarting failed container quote-svc restartCount=6", True),
        ],
        [(260, "KubePodCrashLooping", "quote-svc", "page", "pod quote-svc-7d9f restarting more than 3 times in 15m")],
    ),
    Scenario(
        "inc-008-dependency-timeout",
        "Loan applications slow, some failing",
        "dependency_timeout",
        "fraud-score, a downstream dependency, slowed to ~9s p99; application-api calls timed out and the circuit breaker opened.",
        ["application-api", "fraud-score"],
        [
            (100, "WARN", "fraud-score", "p99 latency 9120ms over last 5m (normal ~180ms)", True),
            (130, "ERROR", "application-api", "call to fraud-score timed out after 5000ms path=/v1/score", True),
            (160, "ERROR", "application-api", "circuit breaker fraud-score OPEN after 50% failures in 20 calls", True),
            (170, "ERROR", "application-api", "call to fraud-score timed out after 5000ms path=/v1/score", True),
        ],
        [(150, "ApplicationApiLatencyHigh", "application-api", "page", "p95 above 3s for 5m")],
    ),
    Scenario(
        "inc-009-rate-limit",
        "Credit checks failing intermittently",
        "upstream_rate_limit",
        "bureau-adapter exceeded the external bureau API's request quota after a batch re-run and got HTTP 429s.",
        ["bureau-adapter", "batch-scheduler"],
        [
            (40, "INFO", "batch-scheduler", "manual re-run started job=nightly-rescore records=120000", True),
            (90, "WARN", "bureau-adapter", "upstream bureau-api responded 429 Too Many Requests retry-after=60", True),
            (95, "ERROR", "bureau-adapter", "credit check failed after 3 retries: HTTP 429 quota exceeded", True),
            (150, "WARN", "bureau-adapter", "upstream bureau-api responded 429 Too Many Requests retry-after=60", True),
        ],
        [(140, "BureauAdapterErrorRatio", "bureau-adapter", "page", "error ratio above 10%")],
    ),
    Scenario(
        "inc-010-credential-rotation",
        "Billing service cannot reach its database",
        "credential_rotation",
        "The billing database password was rotated, but billing-svc kept the old value; logins failed.",
        ["billing-svc", "secrets-operator", "postgres-billing"],
        [
            (30, "INFO", "secrets-operator", "rotated secret billing-db-credentials version=7", True),
            (90, "ERROR", "postgres-billing", 'FATAL: password authentication failed for user "billing_app"', True),
            (
                92,
                "ERROR",
                "billing-svc",
                'could not open connection: FATAL: password authentication failed for user "billing_app"',
                True,
            ),
            (120, "WARN", "billing-svc", "connection pool has 0 healthy connections, retrying", False),
        ],
        [(150, "BillingSvcDown", "billing-svc", "page", "readiness probe failing on all pods")],
    ),
    Scenario(
        "inc-011-noise-only",
        "Single short alert, no clear incident",
        "unknown",
        "No incident: one flapping alert and routine traffic. The right answer is to say evidence is insufficient.",
        ["web-frontend", "search-api"],
        [(200, "WARN", "search-api", "slow query took 1250ms index=products", False)],
        [(210, "SearchApiLatencyBlip", "search-api", "ticket", "p99 above 1s for 1m (resolved)")],
    ),
]


def _ts(start: datetime, offset: int) -> str:
    return (start + timedelta(seconds=offset)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _test_card(n: int) -> str:
    """A Luhn-valid 4111 test card number, so the redactor treats it like a real one."""
    body = f"411111111111{n // 10:03d}"
    check = next(d for d in "0123456789" if luhn_ok(body + d))
    return f"{body[:4]} {body[4:8]} {body[8:12]} {body[12:]}{check}"


def build(s: Scenario) -> tuple[list[str], list[dict[str, str]], dict[str, object], dict[str, object]]:
    rng = random.Random(s.id)
    start = datetime.strptime(s.start, "%Y-%m-%dT%H:%M:%SZ")
    rows: list[tuple[int, str, str, str, bool]] = []
    for _ in range(s.noise_lines):
        svc = rng.choice(s.services)
        msg = rng.choice(NOISE).format(
            svc=svc.split("-")[0],
            ms=rng.randint(4, 90),
            r=rng.randint(80, 99),
            email=f"{rng.choice(NAMES)}{rng.randint(1, 99)}@example.com",
            ip=f"203.0.113.{rng.randint(1, 254)}",
            card=_test_card(rng.randint(1000, 9999)),
        )
        rows.append((rng.randint(0, 480), "INFO", svc, msg, False))
    rows += list(s.events)
    rows.sort(key=lambda r: r[0])
    lines, key = [], []
    for n, (off, level, svc, msg, is_key) in enumerate(rows, start=1):
        lines.append(f"{_ts(start, off)} {level} {svc} {msg}")
        if is_key:
            key.append(f"L{n}")
    alerts = [
        {"ts": _ts(start, off), "name": name, "service": svc, "severity": sev, "summary": summ}
        for off, name, svc, sev, summ in s.alerts
    ]
    meta: dict[str, object] = {"id": s.id, "title": s.title, "alerts": alerts}
    label: dict[str, object] = {"category": s.category, "root_cause": s.root_cause, "key_lines": key}
    return lines, alerts, meta, label


def write_all(root: Path) -> list[Path]:
    out = []
    for s in SCENARIOS:
        lines, _, meta, label = build(s)
        d = root / s.id
        d.mkdir(parents=True, exist_ok=True)
        (d / "logs.log").write_text("\n".join(lines) + "\n")
        (d / "incident.yaml").write_text(yaml.safe_dump(meta, sort_keys=False, width=200))
        (d / "label.yaml").write_text(yaml.safe_dump(label, sort_keys=False, width=200))
        out.append(d)
    return out
