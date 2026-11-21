// Types returned by the backend. MUST match backend/app/schemas/*.py
// Change a schema in the backend -> change it here too.

export interface HealthResponse {
  status: 'ok' | 'degraded'
  database: 'up' | 'down'
  version: string
}

export interface PipelineRun {
  log_id: number
  run_id: string
  step: string
  status: 'running' | 'success' | 'warning' | 'failed'
  rows_affected: number | null
  message: string | null
  started_at: string
  finished_at: string | null
}

// ---------------------------------------------------------------------------
// Shared — backend/app/schemas/common.py, ml.py
// ---------------------------------------------------------------------------

/** Slice & dice filters. The date range filters on the booking's ARRIVAL DATE. */
export interface BookingFilter {
  hotel_key: number | null
  date_from: string | null
  date_to: string | null
  channel_group: string | null
  /** ISO alpha-3; 'UNK' = unknown country */
  country_code: string | null
}

/** Rates/averages recomputed from totals; null when the denominator is 0. Money: EUR. */
export interface KpiValues {
  bookings: number
  canceled_bookings: number
  cancellation_rate: number | null
  room_nights_sold: number
  realized_revenue: number
  lost_revenue: number
  net_lost_revenue: number
  adr: number | null
  avg_lead_time: number | null
  avg_los: number | null
}

export interface ModelMetrics {
  model_name: string
  model_version: string
  trained_at: string
  /** {dataset: {metric_name: value}}, e.g. metrics.test.auc */
  metrics: Record<string, Record<string, number>>
}

export interface ModelMetricsResponse {
  models: ModelMetrics[]
}

// ---------------------------------------------------------------------------
// GET /api/filters — schemas/filters.py
// ---------------------------------------------------------------------------

export interface HotelOption {
  hotel_key: number
  hotel_name: string
  hotel_type: string
  city: string
  peak_rooms_occupied: number | null
}

export interface CountryOption {
  country_code: string
  country_name: string
  market_group: string
  bookings: number
}

export interface FilterOptions {
  hotels: HotelOption[]
  channel_groups: string[]
  market_segments: string[]
  countries: CountryOption[]
  arrival_date_range: { min_date: string; max_date: string }
}

// ---------------------------------------------------------------------------
// GET /api/kpi/* — schemas/kpi.py
// ---------------------------------------------------------------------------

export type Grain = 'year' | 'quarter' | 'month' | 'week'

export interface HotelKpi extends KpiValues {
  hotel_key: number
  hotel_name: string
}

export interface KpiSummary {
  filters: BookingFilter
  total: KpiValues
  by_hotel: HotelKpi[]
}

export interface KpiPoint extends KpiValues {
  /** 2016 | 2016-Q3 | 2016-07 | 2016-W27 */
  period: string
  period_start: string
  hotel_key: number | null
  hotel_name: string | null
}

export interface KpiTimeseries {
  grain: Grain
  by_hotel: boolean
  filters: BookingFilter
  points: KpiPoint[]
}

// ---------------------------------------------------------------------------
// GET /api/cancellation/* — schemas/cancellation.py
// ---------------------------------------------------------------------------

export type BreakdownDimension =
  | 'lead_time'
  | 'channel'
  | 'deposit_type'
  | 'country'
  | 'market_segment'
  | 'customer_type'
export type RiskBand = 'Low' | 'Medium' | 'High'
/** Risk band filter; 'All' = every band */
export type RiskBandFilter = RiskBand | 'All'
export type HighRiskSort = 'probability' | 'expected_loss'

export interface BreakdownItem {
  key: string
  label: string
  sort_order: number
  bookings: number
  canceled_bookings: number
  cancellation_rate: number | null
  booking_share: number | null
  lost_revenue: number
  net_lost_revenue: number
}

export interface CancellationBreakdown {
  by: BreakdownDimension
  filters: BookingFilter
  overall_cancellation_rate: number | null
  total_bookings: number
  items: BreakdownItem[]
}

export interface HighRiskBooking {
  booking_id: number
  hotel_key: number
  hotel_name: string
  arrival_date: string
  booking_date: string
  lead_time: number
  total_nights: number
  guests: number
  adr: number
  booked_revenue: number
  channel_group: string
  market_segment: string
  country_code: string
  deposit_type: string
  customer_type: string
  total_of_special_requests: number
  previous_cancellations: number
  cancel_probability: number
  risk_band: RiskBand
  expected_loss: number
  is_test_set: boolean
  /** Actual (historical) outcome, unknown at decision time */
  is_canceled: boolean
}

export interface HighRiskPage {
  model_version: string
  filters: BookingFilter
  risk_band: RiskBand | null
  min_probability: number | null
  sort: HighRiskSort
  page: number
  page_size: number
  /** Number of matching bookings (across all pages) */
  total: number
  /** Σ booked revenue of all matching bookings (EUR) */
  booked_revenue_total: number
  /** Σ cancel probability × booked revenue of all matching bookings (EUR) */
  expected_loss_total: number
  items: HighRiskBooking[]
}

// ---------------------------------------------------------------------------
// GET /api/forecast* — schemas/forecast.py
// ---------------------------------------------------------------------------

export interface ForecastPoint {
  week_start_date: string
  predicted_room_nights: number
  lower_bound: number
  upper_bound: number
  actual_room_nights: number | null
  horizon_weeks: number
  is_future: boolean
}

export interface HotelForecast {
  hotel_key: number
  hotel_name: string
  points: ForecastPoint[]
  history: { week_start_date: string; room_nights_sold: number }[]
}

export interface ForecastResponse {
  model_version: string
  available_versions: string[]
  series: HotelForecast[]
}

export interface ForecastMetricsResponse {
  main_model_version: string | null
  models: ModelMetrics[]
}

// ---------------------------------------------------------------------------
// GET /api/channels/ranking, /api/markets/ranking — schemas/ranking.py
// ---------------------------------------------------------------------------

export type RankingSort =
  | 'realized_revenue'
  | 'adr'
  | 'cancellation_rate'
  | 'bookings'
  | 'room_nights_sold'

export interface RankingItem {
  rank: number
  key: string
  label: string
  group: string | null
  bookings: number
  canceled_bookings: number
  cancellation_rate: number | null
  room_nights_sold: number
  realized_revenue: number
  revenue_share: number | null
  lost_revenue: number
  adr: number | null
}

export interface RankingResponse {
  dimension: 'channel' | 'market'
  sort_by: RankingSort
  min_bookings: number
  filters: BookingFilter
  total_realized_revenue: number
  groups_ranked: number
  items: RankingItem[]
}

// ---------------------------------------------------------------------------
// POST /api/what-if — schemas/what_if.py
// ---------------------------------------------------------------------------

/** Omitted fields use the backend defaults. Rates as 0–1. */
export interface WhatIfRequest {
  hotel_key: number
  capacity: number
  overbooking_pct?: number
  deposit_risk_threshold?: number | null
  deposit_rate?: number | null
  deposit_attrition_pct?: number
  walk_cost?: number
  ota_commission?: number
  date_from?: string
  date_to?: string
  max_curve_pct?: number
}

export interface WhatIfAssumptions {
  hotel_key: number
  hotel_name: string
  capacity: number
  overbooking_pct: number
  deposit_risk_threshold: number | null
  deposit_rate: number
  deposit_attrition_pct: number
  walk_cost: number
  ota_commission: number
  date_from: string
  date_to: string
  risk_model_version: string | null
}

export interface WhatIfBaseline {
  nights: number
  room_nights_sold: number
  room_nights_canceled: number
  realized_revenue: number
  adr: number | null
  night_cancellation_rate: number | null
  ota_revenue_share: number | null
  ota_commission_cost: number
  occupancy_rate: number | null
  revpar: number | null
  nights_over_capacity: number
}

export interface WhatIfOverbooking {
  overbooking_pct: number
  extra_reservations: number
  extra_show_ups: number
  rooms_filled: number
  rooms_walked: number
  revenue_recovered: number
  walk_cost_total: number
  net_benefit: number
  nights_with_extra_bookings: number
  nights_at_risk: number
  occupancy_rate_after: number | null
  revpar_after: number | null
}

export interface WhatIfDeposit {
  risk_threshold: number
  deposit_rate: number
  attrition_pct: number
  bookings: number
  flagged_bookings: number
  flagged_canceled: number
  flagged_precision: number | null
  deposit_retained: number
  attrition_loss: number
  net_benefit: number
  in_sample_bookings: number
}

export interface WhatIfCurvePoint {
  overbooking_pct: number
  revenue_recovered: number
  walk_cost_total: number
  net_benefit: number
  rooms_walked: number
  nights_at_risk: number
}

export interface WhatIfResponse {
  assumptions: WhatIfAssumptions
  baseline: WhatIfBaseline
  overbooking: WhatIfOverbooking
  deposit: WhatIfDeposit | null
  total_net_benefit: number
  curve: WhatIfCurvePoint[]
  recommended_overbooking_pct: number
  warnings: string[]
}
