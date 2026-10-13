"""Command line: triage one incident, run the eval, redact a file, regenerate synthetic data."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from . import __version__
from .backends import get_backend
from .evaluate import run_eval
from .evidence import build_pack
from .grounding import check
from .loader import incident_dirs, load_incident
from .redact import redact as redact_text
from .report import to_markdown
from .retrieval import load_runbooks

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Grounded incident triage drafts over logs, alerts and runbooks. Read-only; a human decides.",
)
console = Console()

BACKEND = typer.Option("mock", "--backend", "-b", help="mock (offline), ollama or bedrock")
MODEL = typer.Option(None, "--model", "-m", help="Model id for ollama/bedrock")
RUNBOOKS = typer.Option(Path("runbooks"), "--runbooks", help="Folder of runbook .md files")


@app.command()
def version() -> None:
    """Print the version."""
    console.print(__version__)


@app.command("list")
def list_incidents(root: Path = typer.Argument(Path("incidents"))) -> None:
    """List the synthetic incidents."""
    t = Table("id", "title", "log lines", "alerts")
    for d in incident_dirs(root):
        inc = load_incident(d)
        t.add_row(inc.id, inc.title, str(len(inc.logs)), str(len(inc.alerts)))
    console.print(t)


@app.command()
def triage(
    incident: Path = typer.Argument(..., help="Incident folder with logs.log and incident.yaml"),
    backend: str = BACKEND,
    model: str | None = MODEL,
    runbooks: Path = RUNBOOKS,
    out: Path | None = typer.Option(None, "--out", "-o", help="Write the Markdown brief here"),
    show_prompt: bool = typer.Option(False, help="Print the exact (redacted) prompt an LLM would receive"),
) -> None:
    """Draft a summary + RCA for one incident, with citations and a grounding check."""
    inc = load_incident(incident)
    pack = build_pack(inc, load_runbooks(runbooks))
    if show_prompt:
        from .prompt import SYSTEM, render

        console.print(SYSTEM + "\n\n" + render(pack), markup=False, highlight=False)
        return
    brief = get_backend(backend, model).draft(pack)
    g = check(brief, pack, inc)
    md = to_markdown(brief, pack, g)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md)
    console.print(Markdown(md))
    if not g.hallucination_free:
        raise typer.Exit(2)


@app.command("eval")
def evaluate(
    root: Path = typer.Argument(Path("incidents")),
    backend: str = BACKEND,
    model: str | None = MODEL,
    runbooks: Path = RUNBOOKS,
    out: Path | None = typer.Option(None, "--out", "-o", help="Write JSON results"),
) -> None:
    """Score a backend on the labelled incidents: root cause, citations, hallucinations."""
    s = run_eval(get_backend(backend, model), root, load_runbooks(runbooks))
    t = Table("incident", "expected", "got", "RC", "key line", "cites valid", "no halluc.", title=f"eval: {s.backend}")
    ok = "[green]yes[/green]"
    no = "[red]no[/red]"
    for c in s.cases:
        t.add_row(
            c.incident,
            c.expected,
            c.got + (" [dim](parse err)[/dim]" if c.parse_error else ""),
            ok if c.root_cause_match else no,
            ok if c.key_evidence_cited else no,
            f"{c.citation_validity:.0%}",
            ok if c.hallucination_free else no,
        )
    console.print(t)
    console.print(
        f"[bold]root cause {s.root_cause_accuracy:.0%}[/bold] · key evidence cited {s.key_evidence_rate:.0%} · "
        f"citation validity {s.citation_validity:.0%} · hallucination-free {s.hallucination_free_rate:.0%} · "
        f"parse failures {s.parse_failures} · {s.mean_seconds}s/incident · n={s.n}"
    )
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(s.model_dump(), indent=2) + "\n")


@app.command()
def redact(path: Path = typer.Argument(..., help="Text or log file")) -> None:
    """Print a file with PII and secrets scrubbed (what an LLM would see)."""
    text, counts = redact_text(path.read_text())
    console.print(text, markup=False, highlight=False, end="")
    console.print(f"[dim]redacted: {counts or 'nothing'}[/dim]")


@app.command()
def synth(root: Path = typer.Argument(Path("incidents"))) -> None:
    """Regenerate the labelled synthetic incidents (deterministic)."""
    from .synth import write_all

    for d in write_all(root):
        console.print(f"wrote {d}")
