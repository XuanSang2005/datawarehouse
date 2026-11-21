-- =============================================================================
-- silver.hotel_bookings — Bookings with types cast and empty values normalized.
-- Source: bronze.hotel_bookings
-- Grain : 1 row = 1 booking
-- Main transformations:
--   * booking_id     : generated identifier (the original dataset has none) = _source_row
--   * 'NULL'/'NA'/'Undefined' : converted to real NULL (except meal: Undefined -> 'SC')
--   * arrival_date   : built from year + month (month name) + day_of_month
--   * booking_date   : arrival_date - lead_time (the day the guest booked)
--   * total_nights   : weekend + week nights
--   * departure_date : arrival_date + total_nights
--   * total_guests   : adults + children + babies
--   * party_type     : Solo / Couple / Family / Group / Other (by number of adults and whether there are children)
--   * country_code   : normalizes 2 codes that are not valid ISO alpha-3 (agreed by the team, see docs/STAR_SCHEMA.md):
--                      'CN' -> 'CAN' (Canada; the dataset has no CAN code), 'TMP' -> 'TLS' (old code for East Timor)
-- Anomalous rows are NOT filtered out here -> see database/checks/ for which rows have issues.
-- ⚠ reservation_status / reservation_status_date contain the booking OUTCOME:
--   kept for descriptive analysis, but NEVER use them as features for the cancellation prediction model.
-- =============================================================================

DROP TABLE IF EXISTS silver.hotel_bookings;

CREATE TABLE silver.hotel_bookings AS
WITH src AS (
    SELECT
        b.*,
        make_date(
            b.arrival_date_year::INT,
            EXTRACT(MONTH FROM to_date(b.arrival_date_month, 'FMMonth'))::INT,
            b.arrival_date_day_of_month::INT
        ) AS arrival_date,
        COALESCE(NULLIF(NULLIF(b.children, 'NA'), 'NULL')::INT, 0) AS children_int
    FROM bronze.hotel_bookings AS b
)
SELECT
    _source_row                                                   AS booking_id,
    hotel                                                         AS hotel_name,
    (is_canceled = '1')                                           AS is_canceled,
    lead_time::INT                                                AS lead_time,
    arrival_date,
    (arrival_date - lead_time::INT)                               AS booking_date,
    arrival_date_week_number::INT                                 AS arrival_week_number,
    stays_in_weekend_nights::INT                                  AS weekend_nights,
    stays_in_week_nights::INT                                     AS week_nights,
    (stays_in_weekend_nights::INT + stays_in_week_nights::INT)    AS total_nights,
    (arrival_date + stays_in_weekend_nights::INT
                  + stays_in_week_nights::INT)                    AS departure_date,
    adults::INT                                                   AS adults,
    children_int                                                  AS children,
    babies::INT                                                   AS babies,
    (adults::INT + children_int + babies::INT)                    AS total_guests,
    CASE
        WHEN adults::INT = 0                       THEN 'Other'
        WHEN children_int + babies::INT > 0        THEN 'Family'
        WHEN adults::INT = 1                       THEN 'Solo'
        WHEN adults::INT = 2                       THEN 'Couple'
        ELSE 'Group'
    END                                                           AS party_type,
    CASE WHEN meal = 'Undefined' THEN 'SC' ELSE meal END          AS meal,  -- per the original paper: Undefined = SC
    CASE country
        WHEN 'CN'  THEN 'CAN'
        WHEN 'TMP' THEN 'TLS'
        ELSE NULLIF(NULLIF(country, 'NULL'), 'NA')
    END                                                           AS country_code,
    NULLIF(market_segment, 'Undefined')                           AS market_segment,
    NULLIF(distribution_channel, 'Undefined')                     AS distribution_channel,
    (is_repeated_guest = '1')                                     AS is_repeated_guest,
    previous_cancellations::INT                                   AS previous_cancellations,
    previous_bookings_not_canceled::INT                           AS previous_bookings_not_canceled,
    reserved_room_type,
    assigned_room_type,
    booking_changes::INT                                          AS booking_changes,
    deposit_type,
    NULLIF(NULLIF(agent, 'NULL'), 'NA')::INT                      AS agent_id,
    NULLIF(NULLIF(company, 'NULL'), 'NA')::INT                    AS company_id,
    days_in_waiting_list::INT                                     AS days_in_waiting_list,
    customer_type,
    adr::NUMERIC(10, 2)                                           AS adr,
    required_car_parking_spaces::INT                              AS required_car_parking_spaces,
    total_of_special_requests::INT                                AS total_of_special_requests,
    reservation_status,
    reservation_status_date::DATE                                 AS reservation_status_date
FROM src;

ALTER TABLE silver.hotel_bookings ADD PRIMARY KEY (booking_id);
