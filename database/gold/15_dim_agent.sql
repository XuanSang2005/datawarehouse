-- =============================================================================
-- gold.dim_agent — Dimension đại lý (SCD Type 2-ready)
-- Nguồn : DISTINCT silver.hotel_bookings.agent_id
-- Grain : 1 dòng = 1 phiên bản của 1 đại lý + dòng agent_key = 0 "No agent" (booking không qua đại lý)
-- SCD   : full load nên hiện mỗi đại lý chỉ có 1 phiên bản (valid_from 1900-01-01, valid_to 9999-12-31).
--         Khi nạp incremental: đóng dòng cũ (valid_to, is_current = false), thêm dòng mới với agent_key mới,
--         và fact tra key theo booking_date BETWEEN valid_from AND valid_to.
-- =============================================================================

DROP TABLE IF EXISTS gold.dim_agent CASCADE;

CREATE TABLE gold.dim_agent AS
WITH agents AS (
    SELECT DISTINCT agent_id FROM silver.hotel_bookings WHERE agent_id IS NOT NULL
)
SELECT
    ROW_NUMBER() OVER (ORDER BY agent_id)::INT  AS agent_key,
    agent_id,
    'Agent ' || agent_id                        AS agent_label,
    TRUE                                        AS has_agent,
    DATE '1900-01-01'                           AS valid_from,
    DATE '9999-12-31'                           AS valid_to,
    TRUE                                        AS is_current
FROM agents

UNION ALL

SELECT 0, NULL, 'No agent', FALSE, DATE '1900-01-01', DATE '9999-12-31', TRUE;

ALTER TABLE gold.dim_agent ADD PRIMARY KEY (agent_key);
