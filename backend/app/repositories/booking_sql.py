"""Shared SQL fragments for queries on gold.fact_booking (SELECT only, rule 1).

- `BOOKING_FROM`: fact_booking JOINed with the dimensions commonly used for filtering/grouping.
- `KPI_SUMS`: additive TOTALS. Rates/ADR are NOT computed here but in services/kpi_math.py
  from these totals (rule 8: sum/sum, never an average of averages).
- `build_where`: builds the WHERE clause from a BookingFilter; values are always bind parameters.
"""

from app.schemas.common import BookingFilter

# The "Unknown" member of dim_country (country_key = -1) has a NULL country_code.
# The API uses the code 'UNK' (not a real ISO code) so the frontend can select/filter this group.
UNKNOWN_COUNTRY_CODE = "UNK"
COUNTRY_CODE_SQL = f"coalesce(co.country_code, '{UNKNOWN_COUNTRY_CODE}')"

BOOKING_FROM = """
    FROM gold.fact_booking AS f
    JOIN gold.dim_hotel           AS h  ON h.hotel_key  = f.hotel_key
    JOIN gold.dim_date            AS ad ON ad.date_key  = f.arrival_date_key
    JOIN gold.dim_channel         AS ch ON ch.channel_key = f.channel_key
    JOIN gold.dim_country         AS co ON co.country_key = f.country_key
    JOIN gold.dim_booking_profile AS bp ON bp.booking_profile_key = f.booking_profile_key
"""

KPI_SUMS = """
    sum(f.booking_count)::BIGINT     AS bookings,
    sum(f.is_canceled)::BIGINT       AS canceled_bookings,
    sum(f.room_nights_sold)::BIGINT  AS room_nights_sold,
    coalesce(sum(f.realized_revenue), 0) AS realized_revenue,
    coalesce(sum(f.lost_revenue), 0)     AS lost_revenue,
    coalesce(sum(f.net_lost_revenue), 0) AS net_lost_revenue,
    sum(f.lead_time)::BIGINT         AS sum_lead_time,
    sum(f.total_nights)::BIGINT      AS sum_total_nights
"""

# Lead time bands: MUST match database/gold/53_kpi_cancellation_profile.sql
LEAD_TIME_BAND_ORDER = """
    CASE
        WHEN f.lead_time <= 7   THEN 1
        WHEN f.lead_time <= 30  THEN 2
        WHEN f.lead_time <= 90  THEN 3
        WHEN f.lead_time <= 180 THEN 4
        WHEN f.lead_time <= 365 THEN 5
        ELSE 6
    END
"""
LEAD_TIME_BAND_LABEL = (
    f"(ARRAY['0-7', '8-30', '31-90', '91-180', '181-365', '>365'])[{LEAD_TIME_BAND_ORDER}]"
)


def build_where(flt: BookingFilter, extra: list[str] | None = None) -> tuple[str, dict]:
    """Return ('WHERE ...' clause or '', params dict). Values are never concatenated into SQL."""
    clauses: list[str] = list(extra or [])
    params: dict = {}
    if flt.hotel_key is not None:
        clauses.append("f.hotel_key = :hotel_key")
        params["hotel_key"] = flt.hotel_key
    if flt.date_from is not None:
        clauses.append("ad.full_date >= :date_from")
        params["date_from"] = flt.date_from
    if flt.date_to is not None:
        clauses.append("ad.full_date <= :date_to")
        params["date_to"] = flt.date_to
    if flt.channel_group is not None:
        clauses.append("ch.channel_group = :channel_group")
        params["channel_group"] = flt.channel_group
    if flt.country_code is not None:
        clauses.append(f"{COUNTRY_CODE_SQL} = :country_code")
        params["country_code"] = flt.country_code
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params
