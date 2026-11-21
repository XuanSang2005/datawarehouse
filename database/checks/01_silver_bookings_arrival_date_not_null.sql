-- severity: error
-- Every booking must have a valid arrival date (NULL -> date assembly bug in silver/01).
SELECT booking_id
FROM silver.hotel_bookings
WHERE arrival_date IS NULL;
