-- severity: warning
-- Abnormally high ADR (> €1,000/night). Kept in the fact (a real booking), but worth knowing when analysing.
-- Currently 1 booking has ADR = €5,400 (canceled, so it does not count toward realized revenue).
SELECT booking_id, hotel_key, adr, is_canceled
FROM gold.fact_booking
WHERE adr > 1000;
