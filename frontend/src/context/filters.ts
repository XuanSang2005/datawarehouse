// Filters shared by every page (hotel in the top bar; dates/channel/country in FilterBar).
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
  /** Options from GET /api/filters (null while loading or on error) */
  options: FilterOptions | null
  optionsError: Error | null
  /** Selected hotel (null = both) */
  hotel: HotelOption | null
  /** Query parameters sent to the backend */
  params: FilterParams
}

export const FiltersContext = createContext<FiltersContextValue | null>(null)

export function useFilters(): FiltersContextValue {
  const ctx = useContext(FiltersContext)
  if (!ctx) throw new Error('useFilters must be used inside <FiltersProvider>')
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
