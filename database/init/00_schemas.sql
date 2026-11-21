-- =============================================================================
-- 00_schemas.sql — Creates the Medallion architecture schemas + the meta schema.
-- Idempotent: safe to re-run any number of times.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS bronze;  -- Raw data, kept exactly as the source file (every column is TEXT)
CREATE SCHEMA IF NOT EXISTS silver;  -- Cleaned, typed, normalized data
CREATE SCHEMA IF NOT EXISTS gold;    -- Star schema (fact/dim) + KPI/ML tables read by the backend
CREATE SCHEMA IF NOT EXISTS meta;    -- Pipeline operational info (logs, data quality)

COMMENT ON SCHEMA bronze IS 'Raw layer: source data as-is';
COMMENT ON SCHEMA silver IS 'Cleaned layer: clean, correctly typed data';
COMMENT ON SCHEMA gold   IS 'Serving layer: star schema + tables serving the application';
COMMENT ON SCHEMA meta   IS 'Pipeline metadata: ETL run log';
