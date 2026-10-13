"""Amazon Bedrock via the Converse API.

Credentials come from the standard AWS chain (env vars, ~/.aws profile, SSO, or an instance/IRSA role).
Nothing is read from this repo. Install with: pip install 'aiops-incident-assistant[bedrock]'.
"""

from __future__ import annotations

import os
from typing import Any

from ..evidence import EvidencePack
from ..models import Brief
from ..prompt import SYSTEM, render
from .llm import failed, parse_brief


class BedrockBackend:
    def __init__(self, model: str, region: str | None = None) -> None:
        self.model = model
        self.region = region or os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
        self.name = f"bedrock:{model}"
        self._client: Any = None

    def client(self) -> Any:
        if self._client is None:
            import boto3  # optional dependency

            self._client = boto3.client("bedrock-runtime", region_name=self.region)
        return self._client

    def complete(self, prompt: str) -> str:
        resp = self.client().converse(
            modelId=self.model,
            system=[{"text": SYSTEM}],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"temperature": 0, "maxTokens": 1500},
        )
        return str(resp["output"]["message"]["content"][0]["text"])

    def draft(self, pack: EvidencePack) -> Brief:
        try:
            return parse_brief(self.complete(render(pack)), self.name)
        except ImportError:
            return failed(self.name, "boto3 not installed: pip install 'aiops-incident-assistant[bedrock]'")
        except Exception as e:  # botocore raises many types; record and move on
            return failed(self.name, f"bedrock call failed: {type(e).__name__}: {str(e)[:200]}")
