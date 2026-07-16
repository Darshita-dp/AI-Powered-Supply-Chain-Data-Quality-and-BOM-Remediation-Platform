# BOM Guardian AI — task runner (use `make <target>`; on Windows use Git Bash or `mingw32-make`)

.PHONY: install lint format typecheck test test-unit generate api frontend-dev frontend-build all-checks

install:
	pip install -e ".[dev,api,ml]"

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

all-checks: lint typecheck test
