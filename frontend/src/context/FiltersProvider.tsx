import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { getFilterOptions } from '../api/endpoints'
import { useApi } from '../hooks/useApi'
import { EMPTY_FILTERS, FiltersContext, toParams, type FiltersState } from './filters'

export default function FiltersProvider({ children }: { children: ReactNode }) {
  const [filters, setState] = useState<FiltersState>(EMPTY_FILTERS)
  const options = useApi(getFilterOptions)

  const setFilters = useCallback(
    (patch: Partial<FiltersState>) => setState((f) => ({ ...f, ...patch })),
    [],
  )
  // Keep the hotel picked in the top bar; only clear the FilterBar filters
  const resetFilters = useCallback(
    () => setState((f) => ({ ...EMPTY_FILTERS, hotelKey: f.hotelKey })),
    [],
  )

  const value = useMemo(
    () => ({
      filters,
      setFilters,
      resetFilters,
      options: options.data,
      optionsError: options.error,
      hotel: options.data?.hotels.find((h) => h.hotel_key === filters.hotelKey) ?? null,
      params: toParams(filters),
    }),
    [filters, setFilters, resetFilters, options.data, options.error],
  )

  return <FiltersContext.Provider value={value}>{children}</FiltersContext.Provider>
}
