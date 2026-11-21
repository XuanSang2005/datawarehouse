# etl/: Pipeline orchestration

Python code that **downloads sources → loads bronze → runs the SQL of each layer → runs data quality checks**.
Data transformations are written in SQL under `database/`, **not** here.

```
etl/
├── run_pipeline.py      ▶ Main entry point (CLI)
├── config.py            Paths + reading .env
├── db.py                DB connection, running SQL files
├── run_log.py           Logging to meta.etl_run_log
├── quality.py           Runs database/checks/
├── extract/             Each data source = 1 file + registration in __init__.py (SOURCES)
│   ├── hotel_bookings.py   Hotel Booking Demand (TidyTuesday mirror)
│   ├── pt_holidays.py      Portuguese holidays (holidays library)
│   ├── countries.py        ISO 3166 country codes
│   └── weather.py          Daily weather for Lisbon + Faro (Open-Meteo)
├── load/
│   └── bronze_loader.py CSV → bronze via COPY, header validation
├── Dockerfile           Image for the `etl` service in docker-compose.yml (runs the pipeline once)
└── tests/
```

## Run (from the repo root)
```bash
python -m etl.run_pipeline                    # everything
python -m etl.run_pipeline --from silver      # from silver onwards
python -m etl.run_pipeline --steps checks     # data quality checks only
python -m etl.run_pipeline --refresh-sources  # re-download source files
```

## Run in Docker (no venv needed)
```bash
docker compose run --rm etl                   # needs the DB running: docker compose up -d db
```
Source files downloaded inside the container are kept in the `rawdata` volume (not in `data/raw/` on the host).

## Adding a new data source
1. `etl/extract/<name>.py` with a function `extract(target: Path) -> None` that writes a CSV file to `target`
2. `database/bronze/NN_<name>.sql`: the bronze table, TEXT columns matching the CSV header
3. Add a `Source(...)` to `SOURCES` in `etl/extract/__init__.py`
4. Write the cleaning SQL in `database/silver/`
