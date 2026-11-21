-- severity: error
-- Mọi booking phải có ngày đến hợp lệ (nếu NULL -> lỗi ghép ngày ở silver/01).
SELECT booking_id
FROM silver.hotel_bookings
WHERE arrival_date IS NULL;
