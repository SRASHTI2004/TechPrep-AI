# Convenience targets. On Windows without `make`, run the commands shown in README.md directly.
.PHONY: setup hooks localdb migrate api worker test lint format web eval up-lite up-full down check-files

setup: hooks
	cd backend && uv sync --all-groups
	cd frontend && npm ci

hooks:
	git config core.hooksPath .githooks

localdb:
	cd backend && uv run --group localdb python scripts/localdb.py url

migrate:
	cd backend && uv run alembic upgrade head

api:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

worker:
	cd backend && uv run celery -A app.workers.celery_app worker --loglevel=INFO --concurrency=1 --pool=solo

test:
	cd backend && uv run --group localdb pytest
	cd frontend && npm test

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && npm run lint && npm run typecheck

format:
	cd backend && uv run ruff check --fix . && uv run ruff format .

web:
	cd frontend && npm run dev

eval:
	cd backend && uv run python -m eval.run_eval --ablation

up-lite:
	docker compose up --build

up-full:
	INGESTION_MODE=celery REDIS_URL=redis://redis:6379/0 docker compose --profile full up --build

down:
	docker compose --profile full down

check-files:
	python scripts/check_forbidden_files.py --all
