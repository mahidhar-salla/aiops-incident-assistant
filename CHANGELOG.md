# Changelog

## Unreleased (v0.1.0)

- First working version: `triage`, `eval`, `redact`, `list`, `synth` commands.
- 11 labelled synthetic incidents and 10 generic runbooks.
- Backends: offline `mock`, Ollama, Amazon Bedrock (Converse API).
- Grounding check for invalid citations and unsupported numbers, names and timestamps.
- Redaction: `password:`/JSON secrets, `Authorization: Basic`, spaced SINs, Luhn-checked cards (timestamps are kept) and a separate phone pattern.
- Redaction: secret keys at the end of a longer name (`DB_PASSWORD=`, `GITHUB_TOKEN=`, `aws_secret_access_key =`, `"db_password":`) are redacted too; they used to pass through unchanged.
- Redaction: a quoted secret value (`password="correct horse battery"`, `"client_secret": "a,b;c"`) is redacted up to the closing quote; it used to stop at the first space, comma, semicolon or brace and pass the rest through.
- Redaction: an unquoted secret value with a comma or semicolon in it (`password=abc,def`) is redacted whole; it used to stop at the comma and pass `,def` through. A comma or semicolon followed by the next key (`password=abc,host=db`) or a space still ends the value.
- CI: ruff, mypy (strict), pytest on Python 3.11 to 3.13, stale-data check, offline demo.
