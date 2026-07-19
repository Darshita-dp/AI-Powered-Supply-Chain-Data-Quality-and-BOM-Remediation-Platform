# BOM Guardian AI — task runner (use `make <target>`; on Windows use Git Bash or `mingw32-make`)

.PHONY: install lint format typecheck test test-unit generate api frontend-dev frontend-build screenshots all-checks

install:
	pip install -e ".[dev,api,ml,docs-ai,dbt]"

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy src

test:
	pytest

test-unit:
	pytest tests/unit

generate:
	python -m data_generator.cli generate --profile smoke

api:
	uvicorn api.app.main:app --reload

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

# Capture real screenshots of the running app (see docs/screenshots/).
# Requires: pip install playwright && python -m playwright install chromium
screenshots:
	python scripts/capture_screenshots.py

all-checks: lint typecheck test
