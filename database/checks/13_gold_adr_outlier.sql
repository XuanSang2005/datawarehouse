-- severity: warning
-- ADR bất thường cao (> 1.000 €/đêm). Giữ trong fact (booking thật), nhưng cần biết khi phân tích.
-- Hiện có 1 booking ADR = 5.400 € (đã hủy nên không vào doanh thu thực thu).
SELECT booking_id, hotel_key, adr, is_canceled
FROM gold.fact_booking
WHERE adr > 1000;
