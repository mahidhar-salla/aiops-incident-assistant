"""Local model via Ollama's HTTP API (http://localhost:11434 by default). Nothing leaves the machine."""

from __future__ import annotations

import json
import os
import urllib.request

from ..evidence import EvidencePack
from ..models import Brief
from ..prompt import SYSTEM, render
from .llm import failed, parse_brief


class OllamaBackend:
    def __init__(self, model: str, host: str | None = None, timeout: float = 300) -> None:
        self.model = model
        self.host = (host or os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")).rstrip("/")
        if not self.host.startswith("http"):
            self.host = "http://" + self.host
        self.timeout = timeout
        self.name = f"ollama:{model}"

    def complete(self, prompt: str) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0, "seed": 7, "num_ctx": 8192},
                "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
            }
        ).encode()
        req = urllib.request.Request(f"{self.host}/api/chat", data=body, headers={"Content-Type": "application/json"})  # noqa: S310 (http(s) only, user-configured)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
            return str(json.loads(resp.read())["message"]["content"])

    def draft(self, pack: EvidencePack) -> Brief:
        try:
            return parse_brief(self.complete(render(pack)), self.name)
        except OSError as e:
            return failed(self.name, f"ollama request failed: {e}")
