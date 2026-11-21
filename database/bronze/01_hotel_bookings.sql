-- =============================================================================
-- bronze.hotel_bookings — Verbatim copy of hotel_bookings.csv
-- Source: Antonio, Almeida & Nunes (2019), "Hotel booking demand datasets",
--         Data in Brief 22. CSV version taken from Kaggle / TidyTuesday 2020-02-11.
-- Grain : 1 row = 1 booking (as in the original file)
-- Bronze rule: every column is TEXT, NO cleaning; only technical columns (_xxx) are added.
-- Full load: the table is recreated on every pipeline run.
-- =============================================================================

DROP TABLE IF EXISTS bronze.hotel_bookings;

CREATE TABLE bronze.hotel_bookings (
    hotel                          TEXT,
    is_canceled                    TEXT,
    lead_time                      TEXT,
    arrival_date_year              TEXT,
    arrival_date_month             TEXT,
    arrival_date_week_number       TEXT,
    arrival_date_day_of_month      TEXT,
    stays_in_weekend_nights        TEXT,
    stays_in_week_nights           TEXT,
    adults                         TEXT,
    children                       TEXT,
    babies                         TEXT,
    meal                           TEXT,
    country                        TEXT,
    market_segment                 TEXT,
    distribution_channel           TEXT,
    is_repeated_guest              TEXT,
    previous_cancellations         TEXT,
    previous_bookings_not_canceled TEXT,
    reserved_room_type             TEXT,
    assigned_room_type             TEXT,
    booking_changes                TEXT,
    deposit_type                   TEXT,
    agent                          TEXT,
    company                        TEXT,
    days_in_waiting_list           TEXT,
    customer_type                  TEXT,
    adr                            TEXT,
    required_car_parking_spaces    TEXT,
    total_of_special_requests      TEXT,
    reservation_status             TEXT,
    reservation_status_date        TEXT,
    -- technical columns
    _source_row  BIGINT,                              -- row number in the file (starting at 1)
    _source_file TEXT,
    _loaded_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
