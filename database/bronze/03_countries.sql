-- =============================================================================
-- bronze.countries — ISO 3166-1 country codes + UN M49 regions (as-is)
-- Source: github.com/lukes/ISO-3166-Countries-with-Regional-Codes (all/all.csv)
-- Grain : 1 row = 1 country / territory
-- Column names keep the CSV header (they contain hyphens, so they must be double-quoted).
-- Used to enrich gold.dim_country (country name, continent).
-- =============================================================================

DROP TABLE IF EXISTS bronze.countries;

CREATE TABLE bronze.countries (
    "name"                     TEXT,
    "alpha-2"                  TEXT,
    "alpha-3"                  TEXT,
    "country-code"             TEXT,
    "iso_3166-2"               TEXT,
    "region"                   TEXT,
    "sub-region"               TEXT,
    "intermediate-region"      TEXT,
    "region-code"              TEXT,
    "sub-region-code"          TEXT,
    "intermediate-region-code" TEXT,
    _source_row                BIGINT,
    _source_file               TEXT,
    _loaded_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
