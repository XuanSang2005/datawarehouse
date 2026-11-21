# Lối tắt cho các lệnh hay dùng. Windows không có `make` -> xem lệnh gốc trong README.md.
# Yêu cầu: đã activate venv (source .venv/bin/activate).

.PHONY: help install db-up db-down db-reset db-shell etl backend frontend app-up test lint format

help:            ## Liệt kê các lệnh
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

install:         ## Cài dependency Python + Node
	pip install -r requirements-dev.txt
	cd frontend && npm install

db-up:           ## Bật PostgreSQL (Docker)
	docker compose up -d db

db-down:         ## Tắt PostgreSQL (giữ dữ liệu)
	docker compose down

db-reset:        ## XÓA toàn bộ dữ liệu DB rồi bật lại
	docker compose down -v && docker compose up -d db

db-shell:        ## Mở psql vào DB
	docker compose exec db sh -c 'psql -U $$POSTGRES_USER -d $$POSTGRES_DB'

etl:             ## Chạy toàn bộ pipeline ETL
	python -m etl.run_pipeline

backend:         ## Chạy backend dev (port 8000)
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:        ## Chạy frontend dev (port 5173)
	cd frontend && npm run dev

app-up:          ## Chạy cả hệ thống bằng Docker (demo)
	docker compose --profile app up -d --build

test:            ## Chạy test Python
	pytest

lint:            ## Kiểm tra code style (Python + TS)
	ruff check .
	cd frontend && npm run lint

format:          ## Tự sửa format Python
	ruff check . --fix
	ruff format .
