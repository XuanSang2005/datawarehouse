-- =============================================================================
-- silver.countries — Country codes with columns renamed to snake_case, empty strings normalized to NULL.
-- Source: bronze.countries
-- Grain : 1 row = 1 country (key: country_code = ISO alpha-3)
-- Main transformations:
--   * '' -> NULL
--   * Fill in the region for 2 codes that UN M49 leaves blank but that appear in the booking data:
--     TWN (Taiwan) -> Asia / Eastern Asia; ATA (Antarctica) -> Antarctica
-- =============================================================================

DROP TABLE IF EXISTS silver.countries;

CREATE TABLE silver.countries AS
SELECT
    "alpha-3"                                                AS country_code,
    "alpha-2"                                                AS country_code_alpha2,
    "name"                                                   AS country_name,
    CASE "alpha-3"
        WHEN 'TWN' THEN 'Asia'
        WHEN 'ATA' THEN 'Antarctica'
        ELSE NULLIF("region", '')
    END                                                      AS region,
    CASE "alpha-3"
        WHEN 'TWN' THEN 'Eastern Asia'
        WHEN 'ATA' THEN 'Antarctica'
        ELSE NULLIF("sub-region", '')
    END                                                      AS sub_region
FROM bronze.countries;

ALTER TABLE silver.countries ADD PRIMARY KEY (country_code);
