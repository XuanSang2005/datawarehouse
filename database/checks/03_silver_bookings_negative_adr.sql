-- severity: warning
-- A negative ADR (average daily rate per night) is invalid.
SELECT booking_id, hotel_name, adr
FROM silver.hotel_bookings
WHERE adr < 0;
