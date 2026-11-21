// Bộ lọc dùng chung cho mọi trang (khách sạn ở thanh trên cùng; ngày/kênh/quốc gia ở FilterBar).
import { createContext, useContext } from 'react'
import type { FilterParams } from '../api/endpoints'
import type { FilterOptions, HotelOption } from '../types/api'

export interface FiltersState {
  hotelKey: number | null
  dateFrom: string | null
  dateTo: string | null
  channelGroup: string | null
  countryCode: string | null
}

export const EMPTY_FILTERS: FiltersState = {
  hotelKey: null,
  dateFrom: null,
  dateTo: null,
  channelGroup: null,
  countryCode: null,
}

export interface FiltersContextValue {
  filters: FiltersState
  setFilters: (patch: Partial<FiltersState>) => void
  resetFilters: () => void
  /** Danh mục từ GET /api/filters (null khi đang tải hoặc lỗi) */
  options: FilterOptions | null
  optionsError: Error | null
  /** Khách sạn đang chọn (null = cả hai) */
  hotel: HotelOption | null
  /** Tham số query gửi backend */
  params: FilterParams
}

export const FiltersContext = createContext<FiltersContextValue | null>(null)

export function useFilters(): FiltersContextValue {
  const ctx = useContext(FiltersContext)
  if (!ctx) throw new Error('useFilters phải nằm trong <FiltersProvider>')
  return ctx
}

export function toParams(f: FiltersState): FilterParams {
  return {
    hotel_key: f.hotelKey,
    date_from: f.dateFrom,
    date_to: f.dateTo,
    channel_group: f.channelGroup,
    country_code: f.countryCode,
  }
}
