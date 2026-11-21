-- severity: error
-- fact_booking phải có đúng số booking của silver trừ các dòng bị loại theo quy tắc ở gold/30_fact_booking.sql
-- (không có khách, ADR âm). Lệch nghĩa là một phép JOIN dimension đã làm rơi dòng.
SELECT expected.n AS expected_rows, actual.n AS actual_rows
FROM (SELECT count(*) AS n FROM silver.hotel_bookings WHERE total_guests > 0 AND adr >= 0) AS expected,
     (SELECT count(*) AS n FROM gold.fact_booking) AS actual
WHERE expected.n <> actual.n;
