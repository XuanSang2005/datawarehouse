-- severity: warning
-- Booking 0 đêm lưu trú (đến và đi trong ngày) -> cần quyết định cách tính ADR/doanh thu.
SELECT booking_id, hotel_name, arrival_date, is_canceled
FROM silver.hotel_bookings
WHERE total_nights = 0;
