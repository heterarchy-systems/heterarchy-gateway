UV := uv
PYTHON := 3.14.7t
RUN := $(UV) run --locked --python $(PYTHON)
BFF_RULES_COMMAND := $(RUN) python .agents/python_bff_harness/guardrails/guardrail_runner.py app

.PHONY: sync runtime bff-rules format lint typecheck guards test run check container-config ci

sync:
	$(UV) sync --locked --python $(PYTHON)

runtime:
	$(RUN) python -c "import sys; assert sys.version_info[:3] == (3, 14, 7) and not sys._is_gil_enabled()"

bff-rules:
	$(BFF_RULES_COMMAND)

format:
	$(RUN) ruff format app

lint:
	$(RUN) ruff format --check app
	$(RUN) ruff check app

typecheck:
	$(RUN) pyrefly check

guards: bff-rules

test:
	$(RUN) python -m pytest tests -q

run: runtime
	$(RUN) uvicorn app.bootstrap:create_app --factory --host 127.0.0.1 --port 8799 --loop asyncio --http h11 --workers 1 --limit-concurrency 100

check:
	$(MAKE) runtime
	$(MAKE) lint
	$(MAKE) typecheck
	$(BFF_RULES_COMMAND)
	$(MAKE) test

container-config:
	docker compose config --quiet
	docker build --check .

ci: check
