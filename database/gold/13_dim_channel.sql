-- =============================================================================
-- gold.dim_channel — Sales channel dimension = (market_segment, distribution_channel) combination
-- Source: DISTINCT from silver.hotel_bookings
-- Grain : 1 row = 1 combination present in the data (26 rows)
-- Main transformations:
--   * NULL (source says 'Undefined') -> 'Unknown'
--   * channel_group: compact grouping for the dashboard
--   * is_intermediated: channel through an intermediary (TA/TO, GDS), usually commission-bearing
-- =============================================================================

DROP TABLE IF EXISTS gold.dim_channel CASCADE;

CREATE TABLE gold.dim_channel AS
WITH combos AS (
    SELECT DISTINCT
        COALESCE(market_segment, 'Unknown')       AS market_segment,
        COALESCE(distribution_channel, 'Unknown') AS distribution_channel
    FROM silver.hotel_bookings
)
SELECT
    ROW_NUMBER() OVER (ORDER BY market_segment, distribution_channel)::INT  AS channel_key,
    market_segment,
    distribution_channel,
    CASE market_segment
        WHEN 'Online TA'     THEN 'OTA'
        WHEN 'Offline TA/TO' THEN 'Offline TA/TO'
        WHEN 'Direct'        THEN 'Direct'
        WHEN 'Corporate'     THEN 'Corporate'
        WHEN 'Groups'        THEN 'Groups'
        ELSE 'Other'                                -- Complementary, Aviation, Unknown
    END                                                                     AS channel_group,
    (distribution_channel IN ('TA/TO', 'GDS'))                              AS is_intermediated
FROM combos;

ALTER TABLE gold.dim_channel ADD PRIMARY KEY (channel_key);
ALTER TABLE gold.dim_channel ADD CONSTRAINT uq_dim_channel UNIQUE (market_segment, distribution_channel);
