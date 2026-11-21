# Tourism DSS: a decision support system for a hotel chain

> Course project for **Data Warehouses and Decision Support Systems (CO4031)**
> Topic: *Build a decision support solution utilizing a data warehouse/lake/lakehouse and data analytics*, domain: **Tourism**.

A **lakehouse** (PostgreSQL, Bronze → Silver → Gold architecture) plus a **web application** that helps a hotel group
**reduce losses from cancellations** and **optimize seasonal revenue**.

| Decision maker | Decisions the system supports |
|---|---|
| Revenue Manager | Overbooking level, deposit policy, seasonal pricing |
| Sales & Marketing Manager | Budget allocation across distribution channels and markets |
| General Manager | KPI monitoring, comparison of the 2 hotels |
| Reservations department | List of high-risk bookings to call for confirmation |

Problem details: [`docs/BUSINESS_PROBLEM.md`](docs/BUSINESS_PROBLEM.md)

---

## Architecture at a glance

```
 Data sources           ETL (Python + SQL)                PostgreSQL                  Application
┌──────────────┐     ┌──────────────────┐     ┌────────────────────────────┐     ┌──────────────┐
│ hotel_bookings│ ──▶ │ etl/extract      │ ──▶ │ bronze ─▶ silver ─▶ gold   │ ◀── │ backend      │ ◀── frontend
│ pt_holidays   │     │ etl/load         │     │ (database/*.sql)           │     │ FastAPI :8000│     React :5173
│ countries     │     │ etl/run_pipeline │     │ meta (pipeline log)        │     └──────────────┘
│ weather       │     │                  │     │                            │
└──────────────┘     └──────────────────┘     └────────────────────────────┘
                                                        ▲
                                              ml/ (train) writes results to gold.ml_*
```

Details: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

---

## Directory structure

```
datawarehouse/
├── database/          🗄️  DB: ALL SQL (schemas, tables, transformations, quality checks)
│   ├── init/              Creates the bronze/silver/gold/meta schemas + log tables
│   ├── bronze/            Raw table DDL (every column TEXT)
│   ├── silver/            Cleaning and type-casting SQL
│   ├── gold/              Star schema SQL (fact/dim) + KPIs
│   └── checks/            Data quality check SQL
├── etl/               ⚙️  PIPELINE: Python code that orchestrates, downloads and loads data
│   ├── extract/           Downloads/generates source files into data/raw/
│   ├── load/              Loads CSVs into bronze (COPY)
│   ├── run_pipeline.py    ▶ Main entry point
│   └── tests/
├── ml/                🤖  ANALYTICS: exploratory notebooks + predictive models
├── backend/           🔌  BE: FastAPI, reads only gold/meta, returns JSON
│   └── app/
│       ├── api/routes/    HTTP endpoints
│       ├── services/      Business logic (what-if, recommendations)
│       ├── repositories/  SQL queries
│       ├── schemas/       Request/response types (Pydantic)
│       └── core/          Configuration, DB connection, logging
├── frontend/          🖥️  FE: React + Vite + TypeScript
│   └── src/
│       ├── pages/         One file per page
│       ├── components/    Reusable UI components
│       ├── api/           Functions that call the backend
│       ├── hooks/         Shared React hooks
│       └── types/         Data types (match backend/schemas)
├── data/raw/          📦  Downloaded source files (NOT committed)
├── docs/              📚  Docs: architecture, business problem, data dictionary, troubleshooting
├── deliverables/      📑  Deliverables: slides, report, video link
├── docker-compose.yml     PostgreSQL (+ backend/frontend for the demo)
├── Makefile               Command shortcuts
└── .env.example           Configuration template -> copy to .env
```

**Where to look when something breaks?** See [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md).

---

## First-time setup

### Requirements
- **Python 3.11+**, **Node.js 20+**, **Docker Desktop**
- Git, VS Code (recommended; the repo ships extension recommendations)

### Steps

**1. Clone the repo and create the configuration file**
```bash
git clone https://github.com/XuanSang2005/datawarehouse.git
```
```bash
cd datawarehouse
```
```bash
cp .env.example .env
```

**2. Create the Python environment** (a single venv at the repo root)
```bash
python -m venv .venv
```
macOS/Linux:
```bash
source .venv/bin/activate
```
Windows (PowerShell):
```bash
.venv\Scripts\Activate.ps1
```
```bash
pip install -r requirements-dev.txt
```

**3. Install the frontend**
```bash
cd frontend && npm install && cd ..
```

**4. Start the database**
```bash
docker compose up -d db
```

**5. Run the pipeline**: downloads the data, loads bronze → silver → gold, then runs the quality checks
```bash
python -m etl.run_pipeline
```

**6. Run the application** (open 2 terminals)
```bash
cd backend && uvicorn app.main:app --reload --port 8000
```
```bash
cd frontend && npm run dev
```

Open http://localhost:5173 and go to the **Pipeline** page (`/system`): if everything is green, the setup succeeded.
Auto-generated API docs are at http://localhost:8000/docs.

> Have `make` (macOS/Linux)? Run `make help` to see the shortcuts: `make db-up`, `make etl`, `make backend`…

### Alternative: run everything in Docker (demo, no Python/Node needed)

Only Docker is required. The command below starts the DB, runs the pipeline once in the `etl` container, then starts the backend and frontend:
```bash
docker compose --profile app up -d --build
```
Follow the pipeline and wait for the `✔ Pipeline finished` line (~1 minute the first time, mostly downloading data):
```bash
docker compose logs -f etl
```
Open http://localhost:5173/system. To start over from an empty DB (before a demo):
```bash
docker compose --profile app down -v
```

---

## Common commands

| Task | Command |
|---|---|
| Rerun the full pipeline | `python -m etl.run_pipeline` |
| Rerun only silver + gold (after editing SQL) | `python -m etl.run_pipeline --from silver` |
| Run selected steps | `python -m etl.run_pipeline --steps gold checks` |
| Re-download source files | `python -m etl.run_pipeline --refresh-sources` |
| Test Python | `pytest` |
| Lint | `ruff check .` and `cd frontend && npm run lint` |
| Clean database reset | `docker compose down -v && docker compose up -d db` |
| Run the whole system in Docker (demo) | `docker compose --profile app up -d --build` (see the section above) |
| Run the pipeline in Docker | `docker compose run --rm etl` |

---

## Data

| Source | Description | How it is obtained |
|---|---|---|
| **Hotel Booking Demand** | 119,390 bookings, City Hotel (Lisbon) and Resort Hotel (Algarve), 07/2015–08/2017 | Downloaded automatically (public mirror of the Kaggle dataset) |
| **Portuguese public holidays** | 2013–2018 | Generated with the `holidays` library |
| **ISO 3166 country codes** | Country name, continent (UN M49 regions) | Downloaded automatically (GitHub `lukes/ISO-3166-Countries-with-Regional-Codes`) |
| **Historical weather** | Daily, Lisbon (City Hotel) and Faro (Resort Hotel), 2015–2017: temperature, precipitation, sunshine hours, WMO code | Downloaded automatically ([Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), no key needed) |

Column-by-column description: [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md)

> Source: N. Antonio, A. de Almeida, L. Nunes, "Hotel booking demand datasets", *Data in Brief*, vol. 22, pp. 41–49, 2019.

---

## Documentation

| File | Contents |
|---|---|
| [`docs/BUSINESS_PROBLEM.md`](docs/BUSINESS_PROBLEM.md) | Context, decision makers, objectives |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Architecture, data flow, star schema, technology choices |
| [`docs/STAR_SCHEMA.md`](docs/STAR_SCHEMA.md) | Detailed design of the Gold-layer star schema: grain, every column, measures, implementation plan |
| [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md) | Meaning of every table and column |
| [`docs/GLOSSARY.md`](docs/GLOSSARY.md) | Data warehouse terms used in the project |
| [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) | Which error, where to look, how to fix it |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Team workflow: branches, commits, PRs, code conventions |
| [`deliverables/README.md`](deliverables/README.md) | Deadlines and naming rules for submitted files |

## Team members

| Full name | Student ID | Role |
|---|---|---|
| _TBD_ | | |
