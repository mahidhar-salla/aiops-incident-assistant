# Safety notes

This is a drafting tool for people on call. These are the rules it's built around.

## What the AI does
- Reads the log lines and alerts you hand it, after redaction.
- Retrieves sections from the runbooks in `runbooks/`.
- Writes a draft summary, likely root cause, timeline and "what to check next", each citing evidence ids.

## What it doesn't do
- No commands, no API calls to your infrastructure, no tickets, no pages, no remediation. The code has no path to do any of these.
- It doesn't decide severity or customer impact. A human does.

## Human review
- Every brief is marked DRAFT and lists the exact lines and runbook sections it used.
- The grounding check fails the brief (exit code 2) when it cites ids that weren't in the evidence, or mentions numbers, service names or timestamps that don't appear there.
- The check is lexical. It can't tell whether a real line supports the claim it's attached to. Read the cited lines.

## Data handling
- `redact.py` replaces emails, public IPv4 addresses (private ranges are kept as useful infra evidence), card-like and SIN/SSN-like numbers, bearer tokens, AWS access key ids and `password=`, `secret=`, `token=`, `api_key=` values.
- Only WARN/ERROR lines and change events (deploys, rotations, re-runs, rebalances, restarts) go into the prompt; routine INFO lines are dropped.
- Use `aiops-assistant triage <incident> --show-prompt` to see exactly what a model would receive.
- Pattern-based redaction misses things. Don't feed it data you aren't allowed to send to the chosen backend.

## Backends and credentials
- `mock`: deterministic, offline, no model.
- `ollama`: local HTTP API (default `http://127.0.0.1:11434`, override with `OLLAMA_HOST`). Data stays on the machine.
- `bedrock`: boto3 with the standard AWS credential chain. No keys in the repo or config. The redacted prompt goes to Bedrock in the account and region you choose; check your organisation's data rules first.
