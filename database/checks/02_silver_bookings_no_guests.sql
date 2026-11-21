-- severity: warning
-- Bookings with no guests at all (adults = children = babies = 0) -> anomalous data.
-- Whether to filter or keep them is decided in the Gold layer.
SELECT booking_id, hotel_name, arrival_date
FROM silver.hotel_bookings
WHERE adults = 0 AND children = 0 AND babies = 0;
