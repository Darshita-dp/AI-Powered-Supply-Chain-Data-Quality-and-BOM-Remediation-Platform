# Contributing

This is a solo portfolio project, but standard hygiene applies.

## Setup

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows Git Bash
pip install -e ".[dev,api,ml]"
pre-commit install
cd frontend && npm install
```

## Checks before committing

```bash
ruff check . && ruff format --check .
mypy src
pytest
cd frontend && npm run lint && npm run typecheck && npm test -- --run && npm run build
```

## Conventions

- Conventional-commit messages (`feat:`, `fix:`, `docs:`, `chore:`, `ci:`, `test:`).
- One milestone per commit where practical; no broken commits.
- Never commit secrets, `.env`, generated data, or model artifacts.
- Follow the truthfulness rules in [CLAUDE.md](CLAUDE.md) for all documentation.
