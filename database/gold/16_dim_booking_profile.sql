-- =============================================================================
-- gold.dim_booking_profile — Junk dimension: groups the booking's low-cardinality codes/flags
-- Source: DISTINCT combinations present in silver.hotel_bookings
-- Grain : 1 row = 1 combination (meal, deposit_type, customer_type, is_repeated_guest, party_type)
--         ~150 rows, theoretical maximum 4 × 3 × 4 × 2 × 5 = 480
-- =============================================================================

DROP TABLE IF EXISTS gold.dim_booking_profile CASCADE;

CREATE TABLE gold.dim_booking_profile AS
WITH combos AS (
    SELECT DISTINCT meal, deposit_type, customer_type, is_repeated_guest, party_type
    FROM silver.hotel_bookings
)
SELECT
    ROW_NUMBER() OVER (
        ORDER BY meal, deposit_type, customer_type, is_repeated_guest, party_type
    )::INT                                  AS booking_profile_key,
    meal,
    CASE meal
        WHEN 'BB' THEN 'Bed & Breakfast'
        WHEN 'HB' THEN 'Half Board'
        WHEN 'FB' THEN 'Full Board'
        WHEN 'SC' THEN 'Self Catering'
        ELSE meal
    END                                     AS meal_name,
    deposit_type,
    customer_type,
    is_repeated_guest,
    party_type
FROM combos;

ALTER TABLE gold.dim_booking_profile ADD PRIMARY KEY (booking_profile_key);
ALTER TABLE gold.dim_booking_profile ADD CONSTRAINT uq_dim_booking_profile
    UNIQUE (meal, deposit_type, customer_type, is_repeated_guest, party_type);
