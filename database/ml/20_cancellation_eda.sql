-- =============================================================================
-- Data for the cancellation EDA notebook (ml/notebooks/01_claude_eda_cancellation.ipynb): SELECT ONLY.
-- Source: silver.hotel_bookings (119,390 rows, NOT filtered like gold) to reconcile with the figures in
--         docs/BUSINESS_PROBLEM.md, plus an in_gold flag telling whether the booking is in gold.fact_booking.
-- ⚠ Leakage columns (reservation_status, assigned_room_type, ...) are selected on purpose to PROVE that they
--   leak the outcome. Do NOT use this file for training: features come from 21_cancellation_features.sql.
-- =============================================================================

SELECT
    s.booking_id,
    s.hotel_name,
    s.is_canceled::INT                                   AS is_canceled,
    s.arrival_date,
    EXTRACT(YEAR FROM s.arrival_date)::INT               AS arrival_year,
    EXTRACT(MONTH FROM s.arrival_date)::INT              AS arrival_month,
    s.lead_time,
    s.total_nights,
    s.total_guests,
    s.market_segment,
    s.distribution_channel,
    s.deposit_type,
    s.customer_type,
    s.country_code,
    s.agent_id,
    s.adr,
    s.total_of_special_requests,
    -- Suspected leakage columns
    s.reservation_status,
    s.reservation_status_date,
    s.reserved_room_type,
    s.assigned_room_type,
    s.booking_changes,
    s.days_in_waiting_list,
    s.required_car_parking_spaces,
    (f.booking_id IS NOT NULL)                           AS in_gold
FROM silver.hotel_bookings AS s
LEFT JOIN gold.fact_booking AS f ON f.booking_id = s.booking_id
ORDER BY s.booking_id;
