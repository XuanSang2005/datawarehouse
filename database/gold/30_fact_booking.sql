-- =============================================================================
-- gold.fact_booking — Transaction fact: one row per booking
-- Source: silver.hotel_bookings, JOINed to the 1x dimensions to get surrogate keys
--         + gold.business_assumptions (Non Refund deposit rate)
-- Grain : 1 row = 1 booking. PK = booking_id (degenerate dimension, = bronze._source_row)
-- Filter (agreed by the team): EXCLUDE bookings with no guests (adults + children + babies = 0) and bookings with negative ADR.
--   0-night bookings are kept (revenue = 0, nights = 0, so they do not affect ADR computed from totals).
-- Money measures:
--   booked_revenue   = adr × total_nights
--   realized_revenue = booked_revenue if not canceled           (realized revenue)
--   lost_revenue     = booked_revenue if canceled               (gross loss, upper bound)
--   deposit_retained = booked_revenue × non_refund_deposit_rate if canceled AND deposit_type = 'Non Refund'
--   net_lost_revenue = lost_revenue - deposit_retained          (loss after the retained deposit)
-- ⚠ ADR is non-additive: always compute SUM(realized_revenue) / SUM(room_nights_sold), never SUM/AVG(adr).
-- ⛔ Columns derived from the cancellation OUTCOME, forbidden as ML features: status_date_key, reservation_status,
--   room_nights_sold, realized_revenue, lost_revenue, deposit_retained, net_lost_revenue, cancel_lead_days.
-- =============================================================================

DROP TABLE IF EXISTS gold.fact_booking CASCADE;

CREATE TABLE gold.fact_booking AS
WITH b AS (
    SELECT
        s.*,
        (s.adr * s.total_nights)::NUMERIC(12, 2) AS booked_revenue
    FROM silver.hotel_bookings AS s
    WHERE s.total_guests > 0
      AND s.adr >= 0
),
p AS (
    SELECT param_value AS deposit_rate
    FROM gold.business_assumptions
    WHERE param_name = 'non_refund_deposit_rate'
)
SELECT
    -- Degenerate dimension
    b.booking_id,

    -- Foreign keys
    h.hotel_key,
    to_char(b.booking_date, 'YYYYMMDD')::INT                         AS booking_date_key,
    to_char(b.arrival_date, 'YYYYMMDD')::INT                         AS arrival_date_key,
    to_char(b.departure_date, 'YYYYMMDD')::INT                       AS departure_date_key,
    to_char(b.reservation_status_date, 'YYYYMMDD')::INT              AS status_date_key,
    COALESCE(c.country_key, -1)                                      AS country_key,
    ch.channel_key,
    COALESCE(a.agent_key, 0)                                         AS agent_key,
    rr.room_type_key                                                 AS reserved_room_type_key,
    ra.room_type_key                                                 AS assigned_room_type_key,
    bp.booking_profile_key,

    -- Other degenerate dimensions
    b.company_id,
    b.reservation_status,

    -- Measures: counts
    1::SMALLINT                                                      AS booking_count,
    b.is_canceled::INT::SMALLINT                                     AS is_canceled,
    b.lead_time,
    b.weekend_nights,
    b.week_nights,
    b.total_nights,
    CASE WHEN b.is_canceled THEN 0 ELSE b.total_nights END           AS room_nights_sold,
    b.adults,
    b.children,
    b.babies,
    b.total_guests                                                   AS guests,

    -- Measures: money
    b.adr,
    b.booked_revenue,
    CASE WHEN b.is_canceled THEN 0 ELSE b.booked_revenue END::NUMERIC(12, 2)
                                                                     AS realized_revenue,
    CASE WHEN b.is_canceled THEN b.booked_revenue ELSE 0 END::NUMERIC(12, 2)
                                                                     AS lost_revenue,
    CASE WHEN b.is_canceled AND b.deposit_type = 'Non Refund'
         THEN b.booked_revenue * p.deposit_rate ELSE 0 END::NUMERIC(12, 2)
                                                                     AS deposit_retained,
    CASE WHEN b.is_canceled
         THEN b.booked_revenue * (1 - CASE WHEN b.deposit_type = 'Non Refund' THEN p.deposit_rate ELSE 0 END)
         ELSE 0 END::NUMERIC(12, 2)                                  AS net_lost_revenue,

    -- Measures: guest behaviour
    b.days_in_waiting_list,
    b.previous_cancellations,
    b.previous_bookings_not_canceled,
    b.total_of_special_requests,
    b.required_car_parking_spaces,
    b.booking_changes,                                                                    -- ⚠ leakage
    (b.reserved_room_type <> b.assigned_room_type)::INT::SMALLINT    AS is_room_changed,  -- ⚠ leakage
    CASE WHEN b.is_canceled THEN b.arrival_date - b.reservation_status_date END
                                                                     AS cancel_lead_days  -- ⛔ leakage
FROM b
CROSS JOIN p
JOIN gold.dim_hotel           AS h  ON h.hotel_name = b.hotel_name
LEFT JOIN gold.dim_country    AS c  ON c.country_code = b.country_code
JOIN gold.dim_channel         AS ch ON ch.market_segment = COALESCE(b.market_segment, 'Unknown')
                                   AND ch.distribution_channel = COALESCE(b.distribution_channel, 'Unknown')
LEFT JOIN gold.dim_agent      AS a  ON a.agent_id = b.agent_id AND a.is_current
JOIN gold.dim_room_type       AS rr ON rr.room_type_code = b.reserved_room_type
JOIN gold.dim_room_type       AS ra ON ra.room_type_code = b.assigned_room_type
JOIN gold.dim_booking_profile AS bp ON bp.meal = b.meal
                                   AND bp.deposit_type = b.deposit_type
                                   AND bp.customer_type = b.customer_type
                                   AND bp.is_repeated_guest = b.is_repeated_guest
                                   AND bp.party_type = b.party_type;

ALTER TABLE gold.fact_booking ADD PRIMARY KEY (booking_id);

ALTER TABLE gold.fact_booking
    ADD CONSTRAINT fk_fact_booking_hotel          FOREIGN KEY (hotel_key)              REFERENCES gold.dim_hotel (hotel_key),
    ADD CONSTRAINT fk_fact_booking_booking_date   FOREIGN KEY (booking_date_key)       REFERENCES gold.dim_date (date_key),
    ADD CONSTRAINT fk_fact_booking_arrival_date   FOREIGN KEY (arrival_date_key)       REFERENCES gold.dim_date (date_key),
    ADD CONSTRAINT fk_fact_booking_departure_date FOREIGN KEY (departure_date_key)     REFERENCES gold.dim_date (date_key),
    ADD CONSTRAINT fk_fact_booking_status_date    FOREIGN KEY (status_date_key)        REFERENCES gold.dim_date (date_key),
    ADD CONSTRAINT fk_fact_booking_country        FOREIGN KEY (country_key)            REFERENCES gold.dim_country (country_key),
    ADD CONSTRAINT fk_fact_booking_channel        FOREIGN KEY (channel_key)            REFERENCES gold.dim_channel (channel_key),
    ADD CONSTRAINT fk_fact_booking_agent          FOREIGN KEY (agent_key)              REFERENCES gold.dim_agent (agent_key),
    ADD CONSTRAINT fk_fact_booking_reserved_room  FOREIGN KEY (reserved_room_type_key) REFERENCES gold.dim_room_type (room_type_key),
    ADD CONSTRAINT fk_fact_booking_assigned_room  FOREIGN KEY (assigned_room_type_key) REFERENCES gold.dim_room_type (room_type_key),
    ADD CONSTRAINT fk_fact_booking_profile        FOREIGN KEY (booking_profile_key)    REFERENCES gold.dim_booking_profile (booking_profile_key);

CREATE INDEX ix_fact_booking_hotel_arrival ON gold.fact_booking (hotel_key, arrival_date_key);
CREATE INDEX ix_fact_booking_booking_date  ON gold.fact_booking (booking_date_key);
CREATE INDEX ix_fact_booking_channel       ON gold.fact_booking (channel_key);
CREATE INDEX ix_fact_booking_country       ON gold.fact_booking (country_key);
