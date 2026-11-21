-- severity: warning
-- Bookings with 0 nights (arrive and leave the same day) -> need a decision on how to compute ADR/revenue.
SELECT booking_id, hotel_name, arrival_date, is_canceled
FROM silver.hotel_bookings
WHERE total_nights = 0;
