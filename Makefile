# aiops-incident-assistant. `make demo` is the one command to try: Python 3.11+, no network or keys.
PYTHON  ?= python3
VENV    ?= .venv
BIN     := $(VENV)/bin
BACKEND ?= mock
MODEL   ?=
OUT     ?= out
INC     ?= incidents/inc-001-db-pool
M       := $(if $(MODEL),-m $(MODEL),)

.DEFAULT_GOAL := help
.PHONY: help install demo eval eval-ollama test lint fmt data check-data ci clean

help: ## Show targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

$(BIN)/aiops-assistant: pyproject.toml
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install -q --upgrade pip
	$(BIN)/pip install -q -e ".[dev]"
	@touch $@

install: $(BIN)/aiops-assistant ## Create .venv and install with dev tools

demo: install ## Offline end-to-end demo with the mock backend
	@echo "\n\033[1m1) Eleven labelled synthetic incidents\033[0m"
	@$(BIN)/aiops-assistant list
	@echo "\n\033[1m2) Redaction: what leaves the box (first lines)\033[0m"
	@$(BIN)/aiops-assistant redact $(INC)/logs.log | head -6
	@echo "\n\033[1m3) Draft a cited incident brief ($(BACKEND))\033[0m"
	@$(BIN)/aiops-assistant triage $(INC) -b $(BACKEND) $(M) -o $(OUT)/brief.md
	@echo "\n\033[1m4) Score the backend against every labelled incident\033[0m"
	@$(BIN)/aiops-assistant eval -b $(BACKEND) $(M) -o $(OUT)/eval-$(BACKEND).json

eval: install ## Run the eval (BACKEND=mock|ollama|bedrock MODEL=...)
	$(BIN)/aiops-assistant eval -b $(BACKEND) $(M) -o $(OUT)/eval-$(BACKEND).json

eval-ollama: ## Eval with a local Ollama model (MODEL=qwen2.5:1.5b by default)
	$(MAKE) eval BACKEND=ollama MODEL=$(or $(MODEL),qwen2.5:1.5b)

test: install ## Unit tests
	$(BIN)/pytest

lint: install ## ruff + format check + mypy
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .
	$(BIN)/mypy

fmt: install ## Auto-format
	$(BIN)/ruff format .
	$(BIN)/ruff check --fix .

data: install ## Regenerate incidents/ from the generator
	$(BIN)/aiops-assistant synth incidents > /dev/null

check-data: data ## Fail if committed incidents are stale
	git diff --exit-code -- incidents

ci: lint test check-data ## Everything CI runs
	$(MAKE) demo > /dev/null && echo "demo ok"

clean: ## Remove build output
	rm -rf $(OUT) .pytest_cache .ruff_cache .mypy_cache
