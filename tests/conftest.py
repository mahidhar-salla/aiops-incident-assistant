from pathlib import Path

import pytest

from aiops_assistant.retrieval import load_runbooks

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def sections():
    return load_runbooks(ROOT / "runbooks")
