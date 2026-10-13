"""Model backends. All of them take an EvidencePack and return a Brief."""

from __future__ import annotations

from typing import Protocol

from ..evidence import EvidencePack
from ..models import Brief


class Backend(Protocol):
    name: str

    def draft(self, pack: EvidencePack) -> Brief: ...


def get_backend(name: str, model: str | None = None) -> Backend:
    if name == "mock":
        from .mock import MockBackend

        return MockBackend()
    if name == "ollama":
        from .ollama import OllamaBackend

        return OllamaBackend(model=model or "qwen2.5:1.5b")
    if name == "bedrock":
        from .bedrock import BedrockBackend

        return BedrockBackend(model=model or "anthropic.claude-3-haiku-20240307-v1:0")
    raise ValueError(f"unknown backend {name!r} (mock, ollama, bedrock)")
