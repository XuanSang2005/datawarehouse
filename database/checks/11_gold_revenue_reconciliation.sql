-- severity: error
-- Reconcile the money columns in fact_booking:
--   booked_revenue = realized_revenue + lost_revenue
--   net_lost_revenue = lost_revenue - deposit_retained
SELECT booking_id, booked_revenue, realized_revenue, lost_revenue, deposit_retained, net_lost_revenue
FROM gold.fact_booking
WHERE abs(booked_revenue - realized_revenue - lost_revenue) > 0.01
   OR abs(lost_revenue - deposit_retained - net_lost_revenue) > 0.01;
