-- severity: warning
-- ADR (giá trung bình/đêm) âm là không hợp lệ.
SELECT booking_id, hotel_name, adr
FROM silver.hotel_bookings
WHERE adr < 0;
