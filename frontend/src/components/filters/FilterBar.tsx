// Slice & dice filters: arrival date range, channel group, country. The hotel is picked in the top bar.
// Options come from GET /api/filters; values live in FiltersContext so they persist across pages.
import { useFilters } from '../../context/filters'
import { Cap } from '../common/ledger'

const control =
  'w-full cursor-pointer border-0 border-b border-cedar bg-transparent py-1.5 text-[14.5px] font-medium focus:outline-none focus-visible:border-rifle'

interface Props {
  /** Hide filters that do not apply to the page (e.g. the Channels page hides "Channel" while ranking channels) */
  hide?: ('dates' | 'channel' | 'country')[]
}

export default function FilterBar({ hide = [] }: Props) {
  const { options, filters, setFilters, resetFilters } = useFilters()
  const range = options?.arrival_date_range
  const active = filters.dateFrom || filters.dateTo || filters.channelGroup || filters.countryCode

  return (
    <div className="grid grid-cols-2 items-end gap-x-6 gap-y-4 animate-rise md:grid-cols-[repeat(4,minmax(0,1fr))_auto]">
      {!hide.includes('dates') && (
        <>
          <label className="flex flex-col gap-1">
            <Cap>Arrivals from</Cap>
            <input
              type="date"
              className={control}
              value={filters.dateFrom ?? ''}
              min={range?.min_date}
              max={filters.dateTo ?? range?.max_date}
              onChange={(e) => setFilters({ dateFrom: e.target.value || null })}
            />
          </label>
          <label className="flex flex-col gap-1">
            <Cap>Arrivals to</Cap>
            <input
              type="date"
              className={control}
              value={filters.dateTo ?? ''}
              min={filters.dateFrom ?? range?.min_date}
              max={range?.max_date}
              onChange={(e) => setFilters({ dateTo: e.target.value || null })}
            />
          </label>
        </>
      )}
      {!hide.includes('channel') && (
        <label className="flex flex-col gap-1">
          <Cap>Channel</Cap>
          <select
            className={control}
            value={filters.channelGroup ?? ''}
            onChange={(e) => setFilters({ channelGroup: e.target.value || null })}
          >
            <option value="">All channels</option>
            {options?.channel_groups.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
      )}
      {!hide.includes('country') && (
        <label className="flex flex-col gap-1">
          <Cap>Country</Cap>
          <select
            className={control}
            value={filters.countryCode ?? ''}
            onChange={(e) => setFilters({ countryCode: e.target.value || null })}
          >
            <option value="">All countries</option>
            {options?.countries.map((c) => (
              <option key={c.country_code} value={c.country_code}>
                {c.country_name} ({c.country_code})
              </option>
            ))}
          </select>
        </label>
      )}
      <button
        type="button"
        onClick={resetFilters}
        disabled={!active}
        className="cursor-pointer justify-self-start border border-rifle px-4 py-2 text-[13.5px] font-semibold text-rifle transition-colors hover:bg-kangaroo disabled:cursor-default disabled:border-kangaroo disabled:text-oyster disabled:hover:bg-transparent"
      >
        Clear filters
      </button>
    </div>
  )
}
