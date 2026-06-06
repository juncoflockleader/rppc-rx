# Milestone 1 developer commands.
# Most commands operate on the backend/ package; DATABASE_URL is read from the
# environment (falls back to the local docker-compose Postgres).

DATABASE_URL ?= postgresql://postgres:postgres@localhost:5432/podcast_synthesis
export DATABASE_URL

.PHONY: help db-up db-down migrate install run worker test test-unit test-integration fmt

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  %-18s %s\n", $$1, $$2}'

db-up: ## Start Postgres + Redis (docker compose)
	docker compose up -d
	@echo "waiting for postgres healthy..."
	@until docker compose exec -T postgres pg_isready -U postgres -d podcast_synthesis >/dev/null 2>&1; do sleep 1; done
	@echo "postgres ready."

db-down: ## Stop infra
	docker compose down

migrate: ## Apply all migrations
	psql "$(DATABASE_URL)" -v ON_ERROR_STOP=1 -f backend/migrations/000_apply_all.sql
	@echo "migrations applied."

seed-personas: ## Import persona YAML seeds into the DB + canon index (run after migrate)
	cd backend && python -m app.personas_import

install: ## Install backend (editable) with dev + queue extras
	cd backend && pip install -e ".[dev,queue]"

run: ## Run the API (reload)
	cd backend && uvicorn app.main:app --reload

worker: ## Run a worker (rq mode only; inproc runs inside the API)
	cd backend && JOB_QUEUE_BACKEND=rq python -m app.workers.worker

test: ## Run all tests
	cd backend && pytest -q

test-unit: ## Run unit tests only (no DB needed)
	cd backend && pytest -q tests/unit

test-integration: ## Run integration tests (needs DATABASE_URL)
	cd backend && pytest -q tests/integration

fmt: ## Lint/format check
	cd backend && ruff check app tests
