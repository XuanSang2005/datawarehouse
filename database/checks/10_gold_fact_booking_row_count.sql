-- severity: error
-- fact_booking must have exactly silver's booking count minus the rows excluded by the rules in gold/30_fact_booking.sql
-- (no guests, negative ADR). A mismatch means a dimension JOIN dropped rows.
SELECT expected.n AS expected_rows, actual.n AS actual_rows
FROM (SELECT count(*) AS n FROM silver.hotel_bookings WHERE total_guests > 0 AND adr >= 0) AS expected,
     (SELECT count(*) AS n FROM gold.fact_booking) AS actual
WHERE expected.n <> actual.n;
