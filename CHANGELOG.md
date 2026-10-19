# Changelog

## Unreleased (v0.1.0)

- First working version: `triage`, `eval`, `redact`, `list`, `synth` commands.
- 11 labelled synthetic incidents and 10 generic runbooks.
- Backends: offline `mock`, Ollama, Amazon Bedrock (Converse API).
- Grounding check for invalid citations and unsupported numbers, names and timestamps.
- Redaction: `password:`/JSON secrets, `Authorization: Basic`, spaced SINs, Luhn-checked cards (timestamps are kept) and a separate phone pattern.
- CI: ruff, mypy (strict), pytest on Python 3.11 to 3.13, stale-data check, offline demo.
