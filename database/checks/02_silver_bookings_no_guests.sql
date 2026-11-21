-- severity: warning
-- Booking không có khách nào (adults = children = babies = 0) -> dữ liệu bất thường.
-- Quyết định lọc hay giữ sẽ thực hiện ở lớp Gold.
SELECT booking_id, hotel_name, arrival_date
FROM silver.hotel_bookings
WHERE adults = 0 AND children = 0 AND babies = 0;
