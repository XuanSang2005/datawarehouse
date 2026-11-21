-- =============================================================================
-- gold.dim_channel — Dimension kênh bán = tổ hợp (market_segment, distribution_channel)
-- Nguồn : DISTINCT từ silver.hotel_bookings
-- Grain : 1 dòng = 1 tổ hợp có trong dữ liệu (26 dòng)
-- Biến đổi chính:
--   * NULL (nguồn ghi 'Undefined') -> 'Unknown'
--   * channel_group: nhóm gọn cho dashboard
--   * is_intermediated: kênh qua trung gian (TA/TO, GDS), thường phải trả hoa hồng
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
