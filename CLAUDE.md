# CLAUDE.md

Guidance for the AI assistant (Claude Code), and also a short set of "ground rules" for anyone new to the repo.

## Project
A decision support system (DSS) for a hotel chain: a PostgreSQL lakehouse (bronze → silver → gold)
plus a web app (FastAPI + React). This is the course project for CO4031. Problem: reduce losses from cancellations and optimize revenue.
The main dataset is Hotel Booking Demand (Antonio et al., 2019). See `docs/BUSINESS_PROBLEM.md`.

## Repo map: each kind of work has exactly ONE place
| Task | Place |
|---|---|
| Create/modify tables, data transformations, KPIs | `database/<layer>/NN_name.sql` |
| Data quality checks | `database/checks/NN_name.sql` |
| Add a new data source | `etl/extract/` + register it in `etl/extract/__init__.py` + DDL in `database/bronze/` |
| Pipeline orchestration | `etl/run_pipeline.py` |
| ML models / notebooks | `ml/` |
| API endpoints | `backend/app/api/routes/` → `services/` → `repositories/` |
| UI pages | `frontend/src/pages/` + register in `frontend/src/routes.tsx` |
| Configuration | `.env` at the repo root (template: `.env.example`), shared by everything |

## Commands
```bash
docker compose up -d db                              # start the DB
python -m etl.run_pipeline [--from silver]           # run the pipeline (from the repo root)
cd backend && uvicorn app.main:app --reload          # backend :8000
cd frontend && npm run dev                           # frontend :5173 (proxy /api -> :8000)
pytest && ruff check .                               # Python tests + lint
cd frontend && npm run lint && npm run build         # FE lint + build
```

## Mandatory rules
1. **SQL lives only in `database/`.** The only exception: SELECT statements in `backend/app/repositories/`.
2. **SQL files are numbered `NN_name.sql` and idempotent** (use `DROP ... IF EXISTS` / `CREATE ... IF NOT EXISTS`). The pipeline runs them in file-name order.
3. **Bronze keeps the source as is**: every column is TEXT, no cleaning. Clean in silver, model in gold.
4. **The backend reads only the `gold` and `meta` schemas**: it does not read bronze/silver, does not write business data, and does not train models.
5. **Backend layering**: routes (HTTP) → services (logic) → repositories (SQL). Routes contain no SQL.
6. **The frontend never calls `fetch` directly**; it must go through `src/api/endpoints.ts`. Types in `src/types/api.ts` must match `backend/app/schemas/`.
7. **Prevent data leakage**: do not use `reservation_status`, `reservation_status_date` (and be careful with `assigned_room_type`, `booking_changes`) as features for cancellation prediction. Use a time-based train/test split.
8. **Non-additive measures** (ADR, cancellation rate) must be recomputed from totals (`sum(revenue)/sum(nights)`), never as an average of averages.
9. Do not commit `.env`, `data/raw/*`, `ml/models/*`, or videos.
10. The dataset has no hotel room counts: occupancy and RevPAR are computed only when the user enters capacity as a parameter.
11. **Create a GitHub issue before doing any work** (feature, bug fix, documentation, configuration); this applies to both people and the AI assistant.
    The issue states: context, what to do, and acceptance criteria. No issue, no code changes.
    The PR description must contain `Closes #<issue number>` so the issue closes automatically on merge. Work that comes up midway gets its own issue.

## Conventions
- Language: documentation, comments, commit messages and UI text are in English. Names of variables, tables and columns are in English, `snake_case` (Python/SQL), `camelCase` (TS).
- Commits follow Conventional Commits, with the directory name as scope: `feat(gold): add dim_date`, `fix(backend): ...`. See `CONTRIBUTING.md`.
- Add/modify a table → update `docs/DATA_DICTIONARY.md`. Change the architecture → update `docs/ARCHITECTURE.md`.
- Common errors and where to look: `docs/TROUBLESHOOTING.md`.
