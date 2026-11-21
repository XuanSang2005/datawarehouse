-- severity: error
-- Total room-nights in fact_daily_occupancy must equal the total nights (within the snapshot range)
-- of non-canceled bookings in fact_booking, per hotel.
WITH period AS (
    SELECT min(d.full_date) AS first_night, max(d.full_date) AS last_night
    FROM gold.fact_daily_occupancy AS o
    JOIN gold.dim_date AS d ON d.date_key = o.stay_date_key
),
expected AS (
    SELECT f.hotel_key,
           sum(GREATEST(0, LEAST(dep.full_date - 1, p.last_night) - GREATEST(arr.full_date, p.first_night) + 1))
               AS room_nights
    FROM gold.fact_booking AS f
    JOIN gold.dim_date AS arr ON arr.date_key = f.arrival_date_key
    JOIN gold.dim_date AS dep ON dep.date_key = f.departure_date_key
    CROSS JOIN period AS p
    WHERE f.is_canceled = 0
    GROUP BY f.hotel_key
),
actual AS (
    SELECT hotel_key, sum(rooms_occupied) AS room_nights
    FROM gold.fact_daily_occupancy
    GROUP BY hotel_key
)
SELECT e.hotel_key, e.room_nights AS expected_room_nights, a.room_nights AS actual_room_nights
FROM expected AS e
FULL JOIN actual AS a ON a.hotel_key = e.hotel_key
WHERE e.room_nights IS DISTINCT FROM a.room_nights;
