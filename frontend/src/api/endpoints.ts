// One function here per backend endpoint. Components do NOT call fetch directly.
import { apiGet, apiPost, withQuery } from './client'
import type {
  BookingFilter,
  BreakdownDimension,
  CancellationBreakdown,
  FilterOptions,
  ForecastMetricsResponse,
  ForecastResponse,
  Grain,
  HealthResponse,
  HighRiskPage,
  HighRiskSort,
  KpiSummary,
  KpiTimeseries,
  ModelMetricsResponse,
  PipelineRun,
  RankingResponse,
  RankingSort,
  RiskBandFilter,
  WhatIfRequest,
  WhatIfResponse,
} from '../types/api'

/** Filters the FE sends: every field is optional. */
export type FilterParams = Partial<BookingFilter>

export const getHealth = () => apiGet<HealthResponse>('/api/health')

export const getPipelineRuns = (limit = 50) =>
  apiGet<PipelineRun[]>(`/api/pipeline/runs?limit=${limit}`)

export const getFilterOptions = () => apiGet<FilterOptions>('/api/filters')

export const getKpiSummary = (filters: FilterParams = {}) =>
  apiGet<KpiSummary>(withQuery('/api/kpi/summary', { ...filters }))

export const getKpiTimeseries = (grain: Grain, filters: FilterParams = {}, byHotel = false) =>
  apiGet<KpiTimeseries>(
    withQuery('/api/kpi/timeseries', { ...filters, grain, by_hotel: byHotel }),
  )

export const getCancellationBreakdown = (
  by: BreakdownDimension,
  filters: FilterParams = {},
  topN?: number,
) =>
  apiGet<CancellationBreakdown>(
    withQuery('/api/cancellation/breakdown', { ...filters, by, top_n: topN }),
  )

export interface HighRiskParams extends FilterParams {
  risk_band?: RiskBandFilter
  min_probability?: number | null
  test_set_only?: boolean
  sort?: HighRiskSort
  model_version?: string
  page?: number
  page_size?: number
}

export const getHighRiskBookings = (params: HighRiskParams = {}) =>
  apiGet<HighRiskPage>(withQuery('/api/cancellation/high-risk', { ...params }))

export const getCancellationModelMetrics = () =>
  apiGet<ModelMetricsResponse>('/api/cancellation/model-metrics')

export const getForecast = (hotelKey?: number, modelVersion?: string) =>
  apiGet<ForecastResponse>(
    withQuery('/api/forecast', { hotel_key: hotelKey, model_version: modelVersion }),
  )

export const getForecastMetrics = () => apiGet<ForecastMetricsResponse>('/api/forecast/metrics')

export interface RankingParams extends FilterParams {
  sort_by?: RankingSort
  top_n?: number
  min_bookings?: number
}

export const getChannelRanking = (params: RankingParams = {}) =>
  apiGet<RankingResponse>(withQuery('/api/channels/ranking', { ...params }))

export const getMarketRanking = (params: RankingParams = {}) =>
  apiGet<RankingResponse>(withQuery('/api/markets/ranking', { ...params }))

export const runWhatIf = (body: WhatIfRequest) => apiPost<WhatIfResponse>('/api/what-if', body)
