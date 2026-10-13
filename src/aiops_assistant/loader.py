"""Load an incident directory: logs.log, incident.yaml and (for eval only) label.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

from .models import Alert, Incident, Label, LogLine


def parse_log_line(n: int, raw: str) -> LogLine:
    parts = raw.split(" ", 3)
    if len(parts) < 4:
        return LogLine(id=f"L{n}", ts="", level="INFO", service="unknown", message=raw)
    ts, level, service, message = parts
    return LogLine(id=f"L{n}", ts=ts, level=level, service=service, message=message)


def load_incident(path: Path, with_label: bool = False) -> Incident:
    meta = yaml.safe_load((path / "incident.yaml").read_text())
    raw_lines = (path / "logs.log").read_text().splitlines()
    logs = [parse_log_line(n, raw) for n, raw in enumerate(raw_lines, start=1) if raw.strip()]
    alerts = [Alert(id=f"A{i}", **a) for i, a in enumerate(meta.get("alerts", []), start=1)]
    label = None
    if with_label and (path / "label.yaml").exists():
        label = Label(**yaml.safe_load((path / "label.yaml").read_text()))
    return Incident(id=meta["id"], title=meta["title"], logs=logs, alerts=alerts, label=label)


def incident_dirs(root: Path) -> list[Path]:
    return sorted(p for p in root.iterdir() if (p / "incident.yaml").exists())
