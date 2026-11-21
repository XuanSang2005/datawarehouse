# database/: All of the project's SQL

Every change to **table structure** and **data transformations** lives here.
The pipeline (`etl/run_pipeline.py`) runs the files in **folder order, then file name order**.

| Folder | Runs at step | Contents | Rule |
|---|---|---|---|
| `init/` | init (always runs) | Creates the `bronze/silver/gold/meta` schemas and the log table | `IF NOT EXISTS` |
| `bronze/` | bronze | DDL for raw tables (TEXT), then Python loads the CSV | Column names match the CSV header |
| `silver/` | silver | `CREATE TABLE AS SELECT` that cleans and casts types | No row filtering |
| `gold/` | gold | Star schema, KPIs | Dims `1x` → facts `3x` → KPIs `5x` |
| `checks/` | checks | Data quality checks: a SELECT that returns the violating rows | First line `-- severity: error\|warning` |

## Adding/changing a table
1. Create or edit the `NN_name.sql` file in the right layer, with a header (table name, source, grain, transformations).
2. Re-run from that layer: `python -m etl.run_pipeline --from silver`
3. Update `docs/DATA_DICTIONARY.md`.

## Debugging
- An error printed as `Step 'silver/01_hotel_bookings.sql' failed: ...` means: open that exact file.
- Run individual SQL snippets in psql, DBeaver or VS Code SQLTools.
- Run history: `SELECT * FROM meta.etl_run_log ORDER BY log_id DESC LIMIT 20;`
