# Shortcuts for frequently used commands. Windows has no `make` -> see the raw commands in README.md.
# Requirement: the venv is activated (source .venv/bin/activate).

.PHONY: help install db-up db-down db-reset db-shell etl etl-docker backend frontend app-up app-reset test lint format

help:            ## List the commands
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

install:         ## Install Python + Node dependencies
	pip install -r requirements-dev.txt
	cd frontend && npm install

db-up:           ## Start PostgreSQL (Docker)
	docker compose up -d db

db-down:         ## Stop PostgreSQL (keep data)
	docker compose down

db-reset:        ## DELETE all DB data, then start again
	docker compose down -v && docker compose up -d db

db-shell:        ## Open psql on the DB
	docker compose exec db sh -c 'psql -U $$POSTGRES_USER -d $$POSTGRES_DB'

etl:             ## Run the full ETL pipeline
	python -m etl.run_pipeline

etl-docker:      ## Run the ETL pipeline in Docker (no venv needed)
	docker compose run --rm etl

backend:         ## Run the dev backend (port 8000)
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:        ## Run the dev frontend (port 5173)
	cd frontend && npm run dev

app-up:          ## Run the whole system in Docker (demo): db + etl + backend + frontend
	docker compose --profile app up -d --build

app-reset:       ## DELETE data, then rerun the Docker demo from an empty DB
	docker compose --profile app down -v && docker compose --profile app up -d --build

test:            ## Run Python tests
	pytest

lint:            ## Check code style (Python + TS)
	ruff check .
	cd frontend && npm run lint

format:          ## Auto-fix Python formatting
	ruff check . --fix
	ruff format .
