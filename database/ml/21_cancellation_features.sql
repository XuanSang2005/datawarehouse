-- =============================================================================
-- Input data for the cancellation prediction model (E3): just a SELECT, no table is created.
-- Read by: ml/cancellation/features.py (load_dataset). Not run by etl/run_pipeline.py.
-- Grain : 1 row = 1 booking of gold.fact_booking (every booking gets scored).
-- Columns: booking_id + the is_canceled label + the split column (arrival_date) + columns
--          known AT BOOKING TIME.
-- ⛔ Deliberately does NOT select columns derived from the cancellation outcome (see the header of
--    database/gold/30_fact_booking.sql) or columns only known after booking (room actually given,
--    number of booking modifications, waiting days).
--    Full list + reasons: ml/cancellation/features.py (LEAKAGE_COLUMNS).
--    ml/tests/test_cancellation_features.py checks that this file mentions none of the forbidden columns.
-- =============================================================================

SELECT
    f.booking_id,
    f.is_canceled,
    d.full_date                            AS arrival_date,

    -- Hotel and arrival time
    h.hotel_name,
    d.day_of_week                          AS arrival_day_of_week,
    d.season                               AS arrival_season,
    d.is_holiday                           AS arrival_is_holiday,

    -- How far ahead, how long the stay, how many guests
    f.lead_time,
    f.weekend_nights,
    f.week_nights,
    f.total_nights,
    f.adults,
    f.children,
    f.babies,

    -- Sales channel and agent
    ch.market_segment,
    ch.distribution_channel,
    ag.agent_id,
    f.company_id,

    -- Customer
    co.country_code,
    co.market_group,
    bp.meal,
    bp.deposit_type,
    bp.customer_type,
    bp.is_repeated_guest,
    bp.party_type,
    f.previous_cancellations,
    f.previous_bookings_not_canceled,

    -- Reserved room and price
    rr.room_type_code                      AS reserved_room_type,
    f.adr,
    f.total_of_special_requests
FROM gold.fact_booking            AS f
JOIN gold.dim_hotel               AS h  ON h.hotel_key = f.hotel_key
JOIN gold.dim_date                AS d  ON d.date_key = f.arrival_date_key
JOIN gold.dim_channel             AS ch ON ch.channel_key = f.channel_key
JOIN gold.dim_agent               AS ag ON ag.agent_key = f.agent_key
JOIN gold.dim_country             AS co ON co.country_key = f.country_key
JOIN gold.dim_booking_profile     AS bp ON bp.booking_profile_key = f.booking_profile_key
JOIN gold.dim_room_type           AS rr ON rr.room_type_key = f.reserved_room_type_key
ORDER BY f.booking_id;
