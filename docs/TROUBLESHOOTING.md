# Troubleshooting: which error, where to look

## Step 0: Identify which layer the error is in

Open **http://localhost:5173/system** (the *Pipeline* page):

| The page shows | Error is in | Go to |
|---|---|---|
| The page does not open | **Frontend** is not running | [§4](#4-frontend) |
| "Could not reach the backend" | **Backend** is not running or is on the wrong port | [§3](#3-backend) |
| Backend → Database: `down` | **Database** is not running or `.env` is wrong | [§1](#1-database) |
| The ETL table has a `failed` row | **Pipeline** | [§2](#2-pipeline-etl) |
| Everything is green but the numbers are wrong | **Transformation SQL** (silver/gold) | [§5](#5-wrong-numbers) |

```
Where does the error appear?      Where to look?
─────────────────────────────────────────────────────────────────────────
Browser (F12 → Console)         →  frontend/src/...
Terminal running `npm run dev`  →  frontend/ (build/TypeScript errors)
Terminal running uvicorn        →  backend/app/... (the traceback points to the file)
Terminal running run_pipeline   →  etl/ or database/<layer>/<file>.sql
Table meta.etl_run_log          →  which step failed, error message
GitHub Actions (CI) red         →  Actions tab → which job is red → read the log
```

---

## 1. Database

| Symptom | Cause | Fix |
|---|---|---|
| `Could not connect to DB ... Connection refused` | The DB container is not running | `docker compose up -d db`, then check with `docker compose ps` |
| `password authentication failed` | `.env` differs from when the volume was created | Correct `.env`, **or** reset: `docker compose down -v && docker compose up -d db` |
| `port is already allocated` / `address already in use` | Another PostgreSQL on the machine already uses port 5432 | Set `POSTGRES_PORT=5433` in `.env` |
| `Cannot connect to the Docker daemon` | Docker Desktop is not open | Open Docker Desktop |

View the DB logs:
```bash
docker compose logs db --tail 50
```
Open psql:
```bash
docker compose exec db psql -U dwh -d tourism_dw
```

## 2. Pipeline (ETL)

The pipeline prints **the exact step and file** that failed, for example:
```
ERROR ✘ Step 'silver/01_hotel_bookings.sql' failed: invalid input syntax for type integer: "NA"
```
Meaning: open `database/silver/01_hotel_bookings.sql` and find the column cast with `::INT` whose data contains `"NA"`.

View the run history:
```sql
SELECT step, status, rows_affected, message, started_at
FROM meta.etl_run_log ORDER BY log_id DESC LIMIT 20;
```

| Failed step name | File to open |
|---|---|
| `init/...` | `database/init/` |
| `extract/<source>` | `etl/extract/<source>.py` (network error: retry, or download the file manually into `data/raw/`) |
| `extract/weather_daily` | `etl/extract/weather.py`. See the Open-Meteo table below |
| `bronze/NN_xxx.sql` | `database/bronze/NN_xxx.sql` (DDL) |
| `bronze/load_<source>` | `etl/load/bronze_loader.py`. Usually caused by a **CSV header that does not match the DDL** (the message lists missing/extra columns) |
| `silver/NN_xxx.sql`, `gold/NN_xxx.sql` | That exact SQL file |
| `checks/NN_xxx.sql` (failed) | Data violates an **error** condition. Run the SELECT in the file to see the violating rows |

| Other symptoms | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'etl'` | Must be run **from the repo root**: `python -m etl.run_pipeline` |
| `ModuleNotFoundError: psycopg / pandas...` | The venv is not activated, or `pip install -r requirements-dev.txt` has not been run |
| `relation "silver.xxx" does not exist` | A previous step has not run. Rerun everything: `python -m etl.run_pipeline` |
| Gold runs in the wrong order (fact before dim) | Change the number in the file name: dim `1x`, fact `3x` |
| `checks/05_silver_weather_daily_coverage` or `14_gold_weather_coverage` failed | `data/raw/weather_daily.csv` is outdated or missing days. Re-download: `python -m etl.run_pipeline --refresh-sources` |

**Open-Meteo weather source** (`extract/weather_daily`):

| Message | Cause | Fix |
|---|---|---|
| `Open-Meteo returned HTTP 429, retrying in 2s ...` (WARNING) | Per-minute request limit exceeded | Nothing to do; the extract retries automatically up to 4 times |
| `Open-Meteo returned HTTP 429 ...: Daily API request limit exceeded` | The ~10,000 requests/day limit **per IP** was exceeded (common on university/company networks or VPNs that share an IP) | Switch networks (e.g. 4G) and rerun, or get `weather_daily.csv` from a teammate and put it in `data/raw/`. When the file already exists, the pipeline does not call the API |
| `WeatherDataError: ... Returned dates do not match ...` | The API returned missing/duplicate dates (rare) | Rerun with `--refresh-sources`. A faulty file is never written to `data/raw/` |

**Debugging a single SQL file:** copy the file's content into psql, DBeaver or VS Code SQLTools and run it section by section.

## 2b. Docker demo (`docker compose --profile app up -d --build`)

Test the demo from scratch (recommended before the project defense):
```bash
docker compose --profile app down -v
```
```bash
docker compose --profile app up -d --build
```
```bash
docker compose logs -f etl
```
Wait for `✔ Pipeline finished`, then open http://localhost:5173/system.

| Symptom | Cause | Fix |
|---|---|---|
| The page loads but shows no data, `relation "gold.xxx" does not exist` | The `etl` container has not finished or has failed | `docker compose ps -a` to check whether `etl` shows `Exited (0)`; `docker compose logs etl` to see the failed step, then use the table in §2 |
| `etl` reports `Could not connect to DB` | `db` is not healthy yet, or `.env` differs from when the volume was created | `docker compose logs db`; reset: `docker compose --profile app down -v` |
| SQL/ETL was changed but Docker still runs the old code | The image was not rebuilt | Add `--build`, or run `docker compose build etl` |
| Re-download source files in Docker | The files live in the `rawdata` volume | `docker compose run --rm etl python -m etl.run_pipeline --refresh-sources` |
| Build fails with `CERTIFICATE_VERIFY_FAILED` during `pip install` / `npm ci` | The network has an SSL-intercepting proxy (company network) | Build on another network. This is not a bug in the repo |

**Problem found while testing the demo (issue #8):** previously `--profile app` only started db + backend + frontend,
so from an empty DB the application ran but had **no data** (the pipeline had to be run manually in a venv). The `etl` service was added.

## 3. Backend

The traceback in the uvicorn terminal always points to the **file and line** that caused the error. Read it from the bottom up.

| HTTP status code | Meaning | Where to look |
|---|---|---|
| **404** | Wrong path, or the router is not included | `app/api/router.py` |
| **422** | Request parameter has the wrong type or is out of range | Parameter declarations in `app/api/routes/*.py`, or `app/schemas/` |
| **500** | Python code error | Traceback → usually in `app/services/` |
| **503** `Database error` | SQL error or lost DB connection | `app/repositories/*.py`; look for the log line `Database error at ...` |
| `ResponseValidationError` | Returned data does not match the schema | Compare the repository with `app/schemas/` |

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'app'` | Run uvicorn **from inside the `backend/` directory** |
| `relation "gold.xxx" does not exist` | The pipeline has not run, or there is no SQL file creating that table in `database/gold/` |

Try the endpoint directly, bypassing the frontend: http://localhost:8000/docs → *Try it out*.

## 4. Frontend

| Symptom | Where to look |
|---|---|
| Blank screen | F12 → Console → the error points to a `src/...` file |
| TypeScript error during `npm run build` | The printed file and line; usually `src/types/api.ts` is out of sync with the backend |
| `Could not reach the backend` | The backend is not running, or `BACKEND_PORT` in `.env` differs from the uvicorn port |
| API call returns 404 | The path in `src/api/endpoints.ts` is wrong |
| Data is displayed wrongly but the API is correct | The component in `src/pages/` or `src/components/` |
| A new page does not show in the navigation | It has not been added to `src/routes.tsx` |

F12 → **Network** → click the `/api/...` request to see what the backend actually returned.

## 5. Wrong numbers

Trace back through the layers (data lineage): **Gold → Silver → Bronze → CSV file**.

```sql
-- Compare row counts across layers
SELECT 'bronze' AS layer, count(*) FROM bronze.hotel_bookings
UNION ALL SELECT 'silver', count(*) FROM silver.hotel_bookings;
-- Look up 1 specific booking in every layer
SELECT * FROM bronze.hotel_bookings WHERE _source_row = 42;
SELECT * FROM silver.hotel_bookings WHERE booking_id = 42;
```

| Common mistake | Cause |
|---|---|
| Aggregated ADR or cancellation rate is off | Using `avg(adr)` instead of `sum(revenue)/sum(nights)` (non-additive measure) |
| Revenue is multiplied | JOIN with a dimension that has duplicate keys (2 dimension rows with the same natural key) |
| Revenue includes cancelled bookings | Missing `WHERE NOT is_canceled` |
| ML model accuracy is close to 100% | **Data leakage**: `reservation_status` is being used as a feature |

## 6. CI (GitHub Actions) is red

Open the **Actions** tab on GitHub → click the red run → the red job:
- **Python (lint + test)**: run `ruff check .` and `pytest` locally to see the errors.
- **ETL pipeline**: run `python -m etl.run_pipeline` locally. CI keeps `data/raw/` in a cache; to make CI download again, change the code in `etl/extract/`.
- **Docker demo**: run the commands in §2b; the logs of every container are in the last step of the job.
- **Frontend**: run `cd frontend && npm run lint && npm run build`.

---

**Still stuck?** Post to the team: (1) the command you ran, (2) the **full** error log, (3) what you have already tried.
