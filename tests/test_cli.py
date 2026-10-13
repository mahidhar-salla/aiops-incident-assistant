import json

from typer.testing import CliRunner

from aiops_assistant.cli import app

runner = CliRunner()


def test_triage_writes_markdown(root, tmp_path, monkeypatch):
    monkeypatch.chdir(root)
    out = tmp_path / "brief.md"
    r = runner.invoke(app, ["triage", "incidents/inc-002-cert-expiry", "-o", str(out)])
    assert r.exit_code == 0, r.output
    md = out.read_text()
    assert "DRAFT" in md and "human must review" in md and "Result: PASS" in md and "`L" in md


def test_show_prompt(root, monkeypatch):
    monkeypatch.chdir(root)
    r = runner.invoke(app, ["triage", "incidents/inc-001-db-pool", "--show-prompt"])
    assert r.exit_code == 0 and "Allowed categories" in r.output and "@example.com" not in r.output


def test_eval_json(root, tmp_path, monkeypatch):
    monkeypatch.chdir(root)
    out = tmp_path / "e.json"
    r = runner.invoke(app, ["eval", "-o", str(out)])
    assert r.exit_code == 0, r.output
    assert json.loads(out.read_text())["backend"] == "mock"


def test_list_and_redact(root, monkeypatch):
    monkeypatch.chdir(root)
    assert "inc-007-oom" in runner.invoke(app, ["list"]).output
    r = runner.invoke(app, ["redact", "incidents/inc-001-db-pool/logs.log"])
    assert r.exit_code == 0 and "@example.com" not in r.output
