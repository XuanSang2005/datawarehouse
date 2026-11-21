-- =============================================================================
-- gold.dim_agent — Agent dimension (SCD Type 2-ready)
-- Source: DISTINCT silver.hotel_bookings.agent_id
-- Grain : 1 row = 1 version of 1 agent + an agent_key = 0 "No agent" row (bookings not made through an agent)
-- SCD   : full load, so each agent currently has only 1 version (valid_from 1900-01-01, valid_to 9999-12-31).
--         With incremental loads: close the old row (valid_to, is_current = false), insert a new row with a new agent_key,
--         and the fact looks up the key by booking_date BETWEEN valid_from AND valid_to.
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
