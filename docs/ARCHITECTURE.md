# System Architecture

## 1. Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   DATA SOURCES                                          │
│   hotel_bookings.csv  pt_holidays (holidays)  countries (ISO 3166)  weather (Open-Meteo) │
└───────────────┬─────────────────────────────────────────────────────────────────────────┘
                │  etl/extract/*.py  ->  data/raw/
                ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         POSTGRESQL (lakehouse, medallion architecture)                   │
│                                                                                          │
│   ┌──────────┐  etl/load  ┌──────────┐  database/  ┌──────────┐  database/  ┌──────────┐ │
│   │ data/raw │ ─────────▶ │  BRONZE  │ ──silver──▶ │  SILVER  │ ───gold───▶ │   GOLD   │ │
│   │  (file)  │   COPY     │ raw, TEXT│   *.sql     │ cleaned  │   *.sql     │ star     │ │
│   └──────────┘            └──────────┘             └──────────┘             │ schema   │ │
│                                                         │                   │ + KPI    │ │
│   ┌──────────┐                                          │ ml/ (train)       │ + ml_*   │ │
│   │   META   │  log of every pipeline step               └──────────────────▶│          │ │
│   └──────────┘                                                              └────┬─────┘ │
└──────────────────────────────────────────────────────────────────────────────────┼───────┘
                                                                                   │ SELECT
                                                         ┌─────────────────────────▼──────┐
                                                         │ BACKEND: FastAPI (:8000)       │
                                                         │ routes → services → repos      │
                                                         └─────────────────────────┬──────┘
                                                                                   │ JSON /api/*
                                                         ┌─────────────────────────▼──────┐
                                                         │ FRONTEND: React + Vite (:5173) │
                                                         │ Dashboard, what-if, forecast   │
                                                         └────────────────────────────────┘
                                                                  ▲
                                                         Decision makers
```

## 2. Components and responsibilities

| Component | Directory | Does | Does NOT do |
|---|---|---|---|
| **Database** | `database/` | Defines schemas and tables; transforms data in SQL; runs quality checks | — |
| **ETL** | `etl/` | Downloads sources, loads bronze, runs SQL in order, writes logs | No data transformations in pandas |
| **ML** | `ml/` | Explores data, trains models, writes results to `gold.ml_*` | Does not serve web requests |
| **Backend** | `backend/` | Reads `gold`/`meta`, computes what-if, returns JSON | Does not read bronze/silver, does not train |
| **Frontend** | `frontend/` | Display and interaction (filters, drill-down, sliders) | Does not compute complex KPIs itself |

## 3. Data flow: medallion architecture

| Layer | Schema | Rules | Example |
|---|---|---|---|
| **Raw files** | `data/raw/` | Downloaded files, never edited by hand | `hotel_bookings.csv` |
| **Bronze** | `bronze` | Keeps 100% of the source as is, every column `TEXT`, adds `_source_row`, `_source_file`, `_loaded_at` | `bronze.hotel_bookings` |
| **Silver** | `silver` | Casts types, normalizes NULLs, adds simple derived columns, **does not filter rows** | `silver.hotel_bookings` (`arrival_date`, `booking_date`, `total_nights`) |
| **Gold** | `gold` | Star schema, surrogate keys, decisions on filtering anomalous data, KPI tables | `gold.fact_booking`, `gold.dim_date` |
| **Meta** | `meta` | Pipeline operations log | `meta.etl_run_log` |

**Load strategy:** *full load*. Every run recreates the tables, because the dataset is static.
A real deployment with new data every day would switch to an *incremental load* on `reservation_status_date`
and use SCD Type 2 for changing dimensions (e.g. agent).

**Pipeline steps** (`etl/run_pipeline.py`):
```
init → extract → bronze → silver → gold → checks
```
Each step, and each SQL file, writes one row to `meta.etl_run_log` (status, row count, error).

## 4. Gold data model: star schema

> Detailed design (every column, grain, measure formulas, agreed decisions): [`STAR_SCHEMA.md`](STAR_SCHEMA.md). SQL: `database/gold/`.

```
                         ┌──────────────┐
                         │  dim_date    │ (role-playing: booking / arrival / departure / status)
                         └──────┬───────┘
     ┌──────────────┐           │           ┌──────────────┐
     │ dim_country  ├───┐       │       ┌───┤  dim_hotel   │ (conformed)
     └──────────────┘   │ ┌─────▼─────┐ │   └──────────────┘
     ┌──────────────┐   ├─┤fact_booking├─┤   ┌──────────────┐
     │ dim_channel  ├───┤ └─────┬─────┘ ├───┤dim_room_type │ (reserved / assigned)
     └──────────────┘   │       │       │   └──────────────┘
     ┌──────────────┐   │       │       │   ┌──────────────┐
     │dim_booking_  ├───┘       │       └───┤  dim_agent   │ (SCD2-ready)
     │profile (junk)│           │           └──────────────┘
     └──────────────┘   ┌───────▼──────────────┐
                        │ fact_daily_occupancy │ (periodic snapshot: 1 row = 1 hotel × 1 night)
                        └──────────┬───────────┘
                                   │ 1 : 1 (hotel_key + date, no row duplication)
                        ┌──────────▼───────────┐
                        │  fact_daily_weather  │ (1 row = 1 hotel × 1 day, Open-Meteo)
                        └──────────────────────┘
```

- **`fact_booking`**: grain = 1 booking (~119,209 rows after removing 181 anomalous rows).
  Measures: `booking_count`, `is_canceled`, `lead_time`, `total_nights`, `room_nights_sold`, `guests`, `adr` (non-additive),
  `booked_revenue`, `realized_revenue`, `lost_revenue`, `deposit_retained`, `net_lost_revenue`, `cancel_lead_days`.
- **`fact_daily_occupancy`**: grain = 1 hotel × 1 night (1,586 rows, 2015-07-01 → 2017-08-31).
  Measures: `rooms_occupied`, `rooms_canceled`, `rooms_booked`, `guests_in_house`, `arrivals`, `departures`, `realized_revenue`, `lost_revenue`. Used for demand forecasting and the overbooking what-if.
- **`fact_daily_weather`**: grain = 1 hotel × 1 day (2,192 rows, 2015–2017; Lisbon for City Hotel, Faro for Resort Hotel).
  Measures: temperature, precipitation, sunshine hours, wind, `is_rainy_day`. The PK equals the join key, so joining with `fact_daily_occupancy` (1:1)
  and `fact_booking` (N:1 on arrival date) does not duplicate rows.
- **Public holidays**: the `is_holiday`, `holiday_name` attributes of `dim_date` (Portuguese national holidays).
- **`kpi_*`** (views): pre-aggregated for each dashboard page. `kpi_daily_occupancy_weather` combines occupancy + calendar + weather per night.
- **`business_assumptions`**: assumed parameters that the dataset lacks (share of the Non Refund deposit retained, default 20%).
- **`ml_booking_risk`**, **`ml_demand_forecast`**, **`ml_model_metrics`**: written by `ml/`.

## 5. Backend: layering

```
HTTP request
   │
   ▼
api/routes/*.py      ← receives parameters, validates (Pydantic), calls services. NO SQL.
   │
   ▼
services/*.py        ← business logic: what-if calculations, overbooking recommendations, data merging.
   │
   ▼
repositories/*.py    ← ONLY SQL SELECT statements on gold/meta, returns list[dict].
   │
   ▼
PostgreSQL
```
- `core/config.py`: reads `.env`. `core/db.py`: shared SQLAlchemy engine.
- DB errors are caught centrally in `main.py`, which returns **HTTP 503** to the FE and logs full details in the backend terminal.
- Business errors (`core/errors.py`) are also caught centrally: `DataNotReadyError` → **HTTP 404** with a `hint`
  (e.g. a `gold.ml_*` table does not exist yet → the command to run the ML script); `InvalidParameterError` → **HTTP 422**.
- Shared filters (`hotel_key`, `date_from`, `date_to` on arrival date, `channel_group`, `country_code`):
  `api/deps.py` reads the query string, `repositories/booking_sql.py` builds the `WHERE` clause with bind parameters.
- Non-additive measures: repositories return only TOTALS; `services/kpi_math.py` computes rates/ADR from the totals (rule 8).
- What-if (`services/what_if_service.py`): pure functions, formulas documented in the docstrings; capacity, compensation
  cost and OTA commission are user-entered parameters (rule 10). Endpoint list: `backend/README.md`.

## 6. Frontend

```
pages/*.tsx ──use──▶ hooks/useApi.ts ──call──▶ api/endpoints.ts ──▶ api/client.ts ──fetch /api/*──▶ Vite proxy ──▶ backend
     │
     └──use──▶ components/ (layout, common, charts, filters)
```
- `routes.tsx` is the single list of pages; both the top navigation bar and the Router read from it.
- Shared filters (`context/FiltersProvider.tsx`): the hotel is chosen in the top bar, arrival date / channel / country in
  `components/filters/FilterBar.tsx`. Values persist across pages and are sent to the backend as query params.
- The frontend **does not compute KPIs**: rates, ADR and what-if all come from the backend; the FE only formats them (`lib/format.ts`, en-GB style).
- The UI follows the prototype in `docs/design/prototype/` (a "ledger" style: paper background, rules instead of cards, one
  Rifle green block per page as the accent, large numbers in Bodoni Moda). Color/font tokens are declared in one place in
  `styles/global.css` (Tailwind's `@theme`) and `lib/theme.ts` (hex values for SVG).

| Page | Users | Main endpoints |
|---|---|---|
| Overview (`/`) | General Manager | `/api/kpi/summary`, `/api/kpi/timeseries` (drill-down Year → Quarter → Month → Week), `/api/channels/ranking` |
| Cancellations (`/cancellation`) | Revenue Manager, Reservations | `/api/cancellation/high-risk` (probability threshold, by arrival week), `/breakdown`, `/model-metrics` |
| Forecast (`/forecast`) | Revenue, Sales & Marketing | `/api/forecast`, `/api/forecast/metrics` |
| What-if (`/what-if`) | Revenue Manager | `POST /api/what-if` (re-requested 300 ms after a slider moves) |
| Channels & markets (`/channels`) | Sales & Marketing | `/api/channels/ranking`, `/api/markets/ranking` |
| Pipeline (`/system`) | Technical team | `/api/health`, `/api/pipeline/runs` |
- Vite proxies `/api` to `localhost:8000` (dev); nginx proxies it to `backend:8000` (Docker). The FE does not need to know the backend URL and avoids CORS errors.

## 7. Configuration and ports

| Variable / Port | Default value | Used by |
|---|---|---|
| `.env` (repo root) | copied from `.env.example` | ETL, backend, Vite, docker compose |
| PostgreSQL | `localhost:5432`, DB `tourism_dw` | |
| Backend | `localhost:8000` (`/docs` = Swagger) | |
| Frontend | `localhost:5173` | |

### Running with Docker (demo)

`docker compose --profile app up -d --build` starts 4 services:

| Service | Image | Role |
|---|---|---|
| `db` | `postgres:16-alpine` | Lakehouse. Data lives in the `pgdata` volume |
| `etl` | `etl/Dockerfile` (context = repo root) | Runs `python -m etl.run_pipeline` **once** and exits, after `db` is healthy. Source files are kept in the `rawdata` volume |
| `backend` | `backend/Dockerfile` | FastAPI, waits for `db` to be healthy (not for `etl`: the System page shows pipeline progress) |
| `frontend` | `frontend/Dockerfile` | nginx serves the build and proxies `/api` to `backend` |

CI has a `docker` job that runs exactly this command from an empty DB, waits for `etl` to exit with code 0, then calls `/api/health` through the frontend.

## 8. Technology choices

| Choice | Rationale | Alternatives considered |
|---|---|---|
| **PostgreSQL + Docker** | Widely used, standard SQL, identical setup for the whole team | DuckDB (hard to share), SQL Server (heavy) |
| **Medallion on 1 DB (separate schemas)** | Shows the lakehouse clearly while staying simple | Parquet on object storage (more than needed) |
| **Plain Python + SQL** | Easy to debug, sufficient for a static dataset, each SQL file is one clear step | dbt, Airflow (time-consuming setup) |
| **FastAPI** | Fast, auto-generated `/docs`, same language (Python) as ETL/ML | Flask, Django |
| **React + Vite + TS** | Rich interactivity (the "interactive" requirement of the criterion worth 50% of the grade), type safety | Streamlit, Power BI |
| **Tailwind CSS v4** | Styles written directly in components, design tokens (the prototype's colors and fonts) declared in one place with `@theme`; no need to name custom classes/CSS per page | Plain CSS (hard to keep consistent with many editors), CSS-in-JS |
| **Recharts** | Declarative React components, all the chart types needed (line, confidence-interval area, scatter, ReferenceArea/Dot), customizable tooltips to match the prototype, lighter than ECharts | Chart.js (imperative API), ECharts (heavy), hand-drawn D3 (laborious) |

## 9. Decision log

| Date | Decision |
|---|---|
| 2026-11-21 | Chose the revenue and cancellation management problem, with the Hotel Booking Demand dataset |
| 2026-11-21 | Stack: PostgreSQL + Python/SQL + FastAPI + React |
| 2026-11-21 | Bronze stores TEXT; silver does not filter rows; decisions on filtering anomalous data are made in gold |
| 2026-11-21 | Finalized the star schema (`STAR_SCHEMA.md`): 7 dimensions, 2 facts, 5 KPI views |
| 2026-11-21 | Removed 181 anomalous rows from the fact; `CN` → `CAN`; assumed 20% of the deposit is retained when a Non Refund booking is cancelled; added the ISO 3166 code source |
| 2026-11-21 | Added the Open-Meteo weather source (Lisbon, Faro) as a separate fact `fact_daily_weather`; added the `etl` service to Docker Compose so the demo runs from an empty DB (issue #8) |
| 2026-11-21 | Backend E5: the API uses the code `UNK` for unknown countries; the what-if only accepts extra bookings on nights that are "full on the books" (booked ≥ capacity), using each night's actual cancellation rate |
| 2026-11-21 | Frontend E6: Tailwind CSS v4 + Recharts, UI following the prototype; added the Channels & markets page; shared filters via React context |
