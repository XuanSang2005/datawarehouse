-- =============================================================================
-- gold.dim_country — Dimension quốc gia của khách
-- Nguồn : mã trong silver.hotel_bookings LEFT JOIN silver.countries (ISO 3166 + vùng UN M49)
-- Grain : 1 dòng = 1 mã quốc gia + 1 dòng Unknown (country_key = -1, cho booking có country NULL)
-- Biến đổi chính:
--   * market_group: Domestic (PRT) / Core Europe (8 thị trường lớn nhất) / Other Europe / Rest of World / Unknown
--   * Mã không tìm thấy trong bảng ISO: country_name = chính mã, region = 'Unknown'
-- =============================================================================

DROP TABLE IF EXISTS gold.dim_country CASCADE;

CREATE TABLE gold.dim_country AS
WITH codes AS (
    SELECT DISTINCT country_code
    FROM silver.hotel_bookings
    WHERE country_code IS NOT NULL
)
SELECT
    ROW_NUMBER() OVER (ORDER BY c.country_code)::INT              AS country_key,
    c.country_code,
    COALESCE(s.country_name, c.country_code)                      AS country_name,
    COALESCE(s.region, 'Unknown')                                 AS region,
    COALESCE(s.sub_region, 'Unknown')                             AS sub_region,
    (c.country_code = 'PRT')                                      AS is_domestic,
    CASE
        WHEN c.country_code = 'PRT'                                             THEN 'Domestic'
        WHEN c.country_code IN ('GBR', 'FRA', 'ESP', 'DEU', 'ITA', 'IRL', 'BEL', 'NLD')
                                                                                THEN 'Core Europe'
        WHEN s.region = 'Europe'                                                THEN 'Other Europe'
        WHEN s.region IS NOT NULL                                               THEN 'Rest of World'
        ELSE 'Unknown'
    END                                                           AS market_group
FROM codes AS c
LEFT JOIN silver.countries AS s ON s.country_code = c.country_code

UNION ALL

SELECT -1, NULL, 'Unknown', 'Unknown', 'Unknown', FALSE, 'Unknown';

ALTER TABLE gold.dim_country ADD PRIMARY KEY (country_key);
ALTER TABLE gold.dim_country ADD CONSTRAINT uq_dim_country_code UNIQUE (country_code);
