// Cancellation risk (G2) — users: Revenue Manager, Reservations team.
// Decisions supported: which bookings to call to reconfirm / ask for a deposit this week; which guest groups cancel most.
// Risk scores come from gold.ml_booking_risk (cancellation model, E3); by default only 2017 bookings (out of sample).
import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import {
  getCancellationBreakdown,
  getCancellationModelMetrics,
  getHighRiskBookings,
} from '../api/endpoints'
import ColumnBars from '../components/charts/ColumnBars'
import DataState from '../components/common/DataState'
import ErrorBox from '../components/common/ErrorBox'
import { BigNumber, Cap, Focal, Money, PageHead, Section, Tabs, td, th } from '../components/common/ledger'
import FilterBar from '../components/filters/FilterBar'
import { useFilters } from '../context/filters'
import { useApi, useDebounced, type ApiState } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { addDays, dateLabel, dayLabel, dayMonth, eur, num, pct } from '../lib/format'
import { hotelColor } from '../lib/theme'
import type { BreakdownDimension, BreakdownItem, CancellationBreakdown, HighRiskBooking, HighRiskSort } from '../types/api'

// The model's test set: bookings arriving in 2017 (data ends 31 Aug 2017)
const FIRST_WEEK = '2017-01-02'
const LAST_WEEK = '2017-08-28'
const DEFAULT_WEEK = '2017-08-21'
const PAGE_SIZE = 25

const LEAD_BANDS: [number, string][] = [
  [7, '0-7'],
  [30, '8-30'],
  [90, '31-90'],
  [180, '91-180'],
  [365, '181-365'],
]
/** Lead time bands — MUST match the backend (repositories/booking_sql.py). */
function leadBand(lead: number): string {
  return LEAD_BANDS.find(([max]) => lead <= max)?.[1] ?? '>365'
}

const DIMENSIONS: { value: BreakdownDimension; label: string }[] = [
  { value: 'lead_time', label: 'Lead time' },
  { value: 'channel', label: 'Channel' },
  { value: 'deposit_type', label: 'Deposit' },
  { value: 'country', label: 'Country' },
]
type Breakdowns = Record<'lead_time' | 'channel' | 'deposit_type' | 'country', CancellationBreakdown>

export default function CancellationPage() {
  const { params } = useFilters()
  const [week, setWeek] = useState(DEFAULT_WEEK)
  const [threshold, setThreshold] = useState<number | null>(null)
  const [sort, setSort] = useState<HighRiskSort>('probability')
  const [pages, setPages] = useState(1)
  const [selected, setSelected] = useState<number | null>(null)
  const [queued, setQueued] = useState<Map<number, string>>(new Map())
  const [toast, showToast] = useToast()

  const metrics = useApi(getCancellationModelMetrics)
  const main = metrics.data?.models.find((m) => m.model_name === 'cancellation_gbm') ?? metrics.data?.models[0]
  const modelThreshold = main?.metrics.validation?.threshold_high ?? 0.5
  const thr = threshold ?? Math.round(modelThreshold * 100) / 100
  const thrQuery = useDebounced(thr, 250)

  // Filters changed → back to the first page
  const listKey = JSON.stringify([params, week, thrQuery, sort])
  useEffect(() => setPages(1), [listKey])

  const weekEnd = addDays(week, 6)
  const list = useApi(
    () =>
      Promise.all(
        Array.from({ length: pages }, (_, i) =>
          getHighRiskBookings({
            ...params,
            date_from: week,
            date_to: weekEnd,
            risk_band: 'All',
            min_probability: thrQuery,
            sort,
            page: i + 1,
            page_size: PAGE_SIZE,
          }),
        ),
      ).then((ps) => ({ ...ps[0], items: ps.flatMap((p) => p.items) })),
    [listKey, pages],
  )

  const bdKey = JSON.stringify({ ...params, date_from: null, date_to: null })
  const breakdowns = useApi(async () => {
    const p = { ...params, date_from: null, date_to: null }
    const [lead_time, channel, deposit_type, country] = await Promise.all([
      getCancellationBreakdown('lead_time', p),
      getCancellationBreakdown('channel', p),
      getCancellationBreakdown('deposit_type', p),
      getCancellationBreakdown('country', p),
    ])
    return { lead_time, channel, deposit_type, country } as Breakdowns
  }, [bdKey])

  const items = list.data?.items ?? []
  const current = items.find((b) => b.booking_id === selected) ?? items[0] ?? null

  const queue = (b: HighRiskBooking, action: string, msg: string) => {
    setQueued((q) => new Map(q).set(b.booking_id, action))
    showToast(msg)
  }

  const canPrev = week > FIRST_WEEK
  const canNext = week < LAST_WEEK
  // "21–27 Aug 2017" within one month, "28 Aug–3 Sep 2017" across months (word joiners: never wrap at the dash)
  const weekStart = week.slice(5, 7) === weekEnd.slice(5, 7) ? String(Number(week.slice(8, 10))) : dayMonth(week)

  return (
    <>
      <PageHead
        title={`Arrivals ${weekStart}\u2060–\u2060${dateLabel(weekEnd)}`}
        aside={
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={!canPrev}
              onClick={() => setWeek((w) => addDays(w, -7))}
              className="cursor-pointer border border-cedar px-3.5 py-2 text-[13.5px] font-semibold hover:bg-kangaroo disabled:cursor-default disabled:opacity-40"
            >
              ← Previous week
            </button>
            <button
              type="button"
              disabled={!canNext}
              onClick={() => setWeek((w) => addDays(w, 7))}
              className="cursor-pointer border border-cedar px-3.5 py-2 text-[13.5px] font-semibold hover:bg-kangaroo disabled:cursor-default disabled:opacity-40"
            >
              Next week →
            </button>
          </div>
        }
      />

      <Focal className="grid items-end gap-x-12 gap-y-5 p-[22px] sm:p-[28px_34px] md:grid-cols-[auto_minmax(0,1fr)] xl:grid-cols-[auto_minmax(0,1fr)_auto]">
        <div>
          <Cap className="text-kangaroo">Likely to cancel</Cap>
          <BigNumber className="text-[clamp(72px,9vw,132px)]">{list.data ? num(list.data.total) : '—'}</BigNumber>
        </div>
        <div className="flex flex-col gap-1.5 pb-2">
          <Cap className="text-kangaroo">Room revenue at risk</Cap>
          <b className="font-display text-[40px] leading-none font-medium tabular-nums">
            {list.data ? <Money value={list.data.expected_loss_total} /> : '—'}
          </b>
          <span className="text-sm text-kangaroo">
            expected = Σ probability × booked revenue · booked {list.data ? eur(list.data.booked_revenue_total) : '—'}
          </span>
        </div>
        <div className="flex min-w-0 flex-col gap-2 pb-2 md:col-span-2 xl:col-span-1 xl:min-w-[260px]">
          <label className="font-mono text-[11.5px] tracking-[0.14em] text-kangaroo uppercase" htmlFor="thr">
            Flag when risk ≥
          </label>
          <div className="flex items-center gap-3.5">
            <input
              id="thr"
              type="range"
              min={5}
              max={95}
              step={1}
              value={Math.round(thr * 100)}
              onChange={(e) => setThreshold(Number(e.target.value) / 100)}
              className="range-ledger range-on-focal"
              style={{ '--p': `${((thr * 100 - 5) / 90) * 100}%` } as CSSProperties}
            />
            <output htmlFor="thr" className="min-w-[74px] text-right font-display text-[34px] leading-none">
              {pct(thr, 0)}
            </output>
          </div>
          <span className="text-[13px] text-kangaroo">Model's High threshold: {pct(modelThreshold, 0)}</span>
        </div>
      </Focal>

      <FilterBar hide={['dates']} />

      <div className="grid items-start animate-rise xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <section className="flex min-w-0 flex-col gap-4 xl:pr-10">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <Cap>
              {list.data ? `${num(items.length)} / ${num(list.data.total)} bookings · ${list.data.model_version}` : ' '}
            </Cap>
            <Tabs
              label="Sort by"
              value={sort}
              onChange={setSort}
              options={[
                { value: 'probability', label: 'Cancel probability' },
                { value: 'expected_loss', label: 'Expected loss' },
              ]}
            />
          </div>
          <DataState
            state={list}
            minHeight={420}
            isEmpty={(d) => d.items.length === 0}
            empty="No bookings above the threshold this week. Try a lower threshold or another week."
          >
            {(d) => (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-[14.5px]">
                  <thead>
                    <tr>
                      <th className={`${th} pl-2.5`}>Booking</th>
                      <th className={th}>Arrival</th>
                      <th className={`${th} text-right`}>Nights</th>
                      <th className={th}>Channel</th>
                      <th className={`${th} text-right`}>Lead</th>
                      <th className={th}>Risk</th>
                    </tr>
                  </thead>
                  <tbody>
                    {d.items.map((b) => {
                      const sel = current?.booking_id === b.booking_id
                      return (
                        <tr
                          key={b.booking_id}
                          tabIndex={0}
                          aria-selected={sel}
                          onClick={() => setSelected(b.booking_id)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault()
                              setSelected(b.booking_id)
                            }
                          }}
                          className={`cursor-pointer transition-colors ${sel ? 'bg-kangaroo' : 'hover:bg-kangaroo/45'}`}
                        >
                          <td className={`${td} pl-2.5`}>
                            <i
                              className="mr-2 inline-block size-2 align-[1px]"
                              style={{ background: hotelColor(b.hotel_name.split(' ')[0]) }}
                              title={b.hotel_name}
                            />
                            <span className="font-mono text-[13.5px] font-semibold">{b.booking_id}</span>
                            {queued.has(b.booking_id) && (
                              <span className="ml-2.5 font-mono text-[11px] tracking-[0.1em] text-rifle uppercase">
                                {queued.get(b.booking_id)}
                              </span>
                            )}
                          </td>
                          <td className={td}>{dayLabel(b.arrival_date)}</td>
                          <td className={`${td} text-right font-mono tabular-nums`}>{b.total_nights}</td>
                          <td className={td}>{b.market_segment}</td>
                          <td className={`${td} text-right font-mono tabular-nums`}>{b.lead_time}d</td>
                          <td className={td}>
                            <div className="flex min-w-[140px] items-center gap-3">
                              <span className="h-1.5 flex-1 overflow-hidden bg-kangaroo">
                                <i className="block h-full bg-rust" style={{ width: `${b.cancel_probability * 100}%` }} />
                              </span>
                              <span className="w-10 text-right font-mono text-[13px] tabular-nums">
                                {pct(b.cancel_probability, 0)}
                              </span>
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
                {items.length < d.total && (
                  <button
                    type="button"
                    onClick={() => setPages((p) => p + 1)}
                    className="mt-4 cursor-pointer border border-rifle px-5 py-2.5 text-sm font-semibold text-rifle hover:bg-kangaroo"
                  >
                    Show {Math.min(PAGE_SIZE, d.total - items.length)} more bookings
                  </button>
                )}
              </div>
            )}
          </DataState>
        </section>

        <BookingDetail
          booking={current}
          threshold={thr}
          breakdowns={breakdowns.data}
          onCall={(b) => queue(b, 'Call', `#${b.booking_id} added to today's reconfirmation calls`)}
          onDeposit={(b) => queue(b, 'Deposit', `Deposit request drafted for #${b.booking_id}`)}
        />
      </div>

      <BreakdownSection state={breakdowns} metrics={main?.metrics ?? null} metricsError={metrics.error} />
      {toast}
    </>
  )
}

interface Factor {
  label: string
  rate: number | null
}

function BookingDetail({
  booking: b,
  threshold,
  breakdowns,
  onCall,
  onDeposit,
}: {
  booking: HighRiskBooking | null
  threshold: number
  breakdowns: Breakdowns | null
  onCall: (b: HighRiskBooking) => void
  onDeposit: (b: HighRiskBooking) => void
}) {
  const overall = breakdowns?.lead_time.overall_cancellation_rate ?? null
  // Factor = HISTORICAL cancellation rate of bookings like this one, compared with the overall rate (not a model explanation)
  const factors: Factor[] = useMemo(() => {
    if (!b || !breakdowns) return []
    const find = (items: BreakdownItem[], key: string) => items.find((i) => i.key === key)?.cancellation_rate ?? null
    return [
      { label: `Booked ${b.lead_time} days ahead`, rate: find(breakdowns.lead_time.items, leadBand(b.lead_time)) },
      { label: `Deposit: ${b.deposit_type}`, rate: find(breakdowns.deposit_type.items, b.deposit_type) },
      { label: `Channel: ${b.channel_group}`, rate: find(breakdowns.channel.items, b.channel_group) },
      { label: `Guests from ${b.country_code}`, rate: find(breakdowns.country.items, b.country_code) },
    ]
  }, [b, breakdowns])

  if (!b) {
    return (
      <aside className="mt-8 border-t border-cedar pt-6 xl:mt-0 xl:border-t-0 xl:border-l xl:pt-0 xl:pl-10">
        <p className="text-oyster-ink">Select a booking to see the details.</p>
      </aside>
    )
  }

  return (
    <aside
      aria-live="polite"
      className="mt-8 flex flex-col gap-6 border-t border-cedar pt-6 xl:sticky xl:top-28 xl:mt-0 xl:border-t-0 xl:border-l xl:pt-0 xl:pl-10"
    >
      <div className="flex items-end justify-between gap-4">
        <div className="font-display text-[84px] leading-[0.82] font-medium tracking-[-0.03em] text-rust tabular-nums sm:text-[104px]">
          {pct(b.cancel_probability, 0)}
        </div>
        <div className="text-right">
          <b className="block font-mono text-base font-medium">#{b.booking_id}</b>
          <Cap>
            {b.hotel_name.replace(' Hotel', '')} · {b.country_code}
          </Cap>
        </div>
      </div>
      <div className="relative h-1.5 bg-kangaroo" title={`Threshold ${pct(threshold, 0)}`}>
        <i className="absolute inset-y-0 left-0 bg-rust" style={{ width: `${b.cancel_probability * 100}%` }} />
        <b className="absolute -top-[7px] -bottom-[7px] w-0.5 bg-cedar" style={{ left: `calc(${threshold * 100}% - 1px)` }} />
      </div>

      {factors.length > 0 && (
        <div className="flex flex-col gap-2.5">
          <Cap>Cancel rate of similar bookings · overall {pct(overall, 0)}</Cap>
          {factors.map((f) => {
            const diff = f.rate != null && overall != null ? f.rate - overall : 0
            const width = Math.min(50, (Math.abs(diff) / 0.5) * 50)
            return (
              <div key={f.label} className="grid grid-cols-[minmax(0,1fr)_110px_44px] items-center gap-3.5 text-[14.5px]">
                <span className="truncate">{f.label}</span>
                <span
                  className="relative h-2 before:absolute before:-top-1 before:-bottom-1 before:left-1/2 before:w-px before:bg-cedar"
                  title={diff > 0 ? 'above the overall rate' : 'below the overall rate'}
                >
                  <i
                    className={`absolute inset-y-0 ${diff > 0 ? 'left-1/2 bg-rust' : 'right-1/2 bg-rifle'}`}
                    style={{ width: `${width}%` }}
                  />
                </span>
                <span className="text-right font-mono text-[13px] tabular-nums">{pct(f.rate, 0)}</span>
              </div>
            )
          })}
        </div>
      )}

      <dl className="m-0 grid grid-cols-2 gap-x-[18px] gap-y-3.5 border-t border-kangaroo pt-[18px] sm:grid-cols-3">
        {(
          [
            ['Arrival', dayLabel(b.arrival_date)],
            ['Nights', b.total_nights],
            ['Deposit', b.deposit_type],
            ['Segment', b.market_segment],
            ['ADR', eur(b.adr)],
            ['Revenue', eur(b.booked_revenue)],
            ['Booked on', dateLabel(b.booking_date)],
            ['Special requests', b.total_of_special_requests],
            ['Past cancellations', b.previous_cancellations],
          ] as [string, string | number][]
        ).map(([k, v]) => (
          <div key={k}>
            <dt>
              <Cap>{k}</Cap>
            </dt>
            <dd className="mt-0.5 font-semibold tabular-nums">{v}</dd>
          </div>
        ))}
      </dl>
      <div className="flex flex-wrap gap-2.5">
        <button
          type="button"
          onClick={() => onCall(b)}
          className="cursor-pointer border border-rifle bg-rifle px-5 py-3 text-sm font-semibold text-merino transition hover:border-cedar hover:bg-cedar active:scale-[0.97]"
        >
          Call to reconfirm
        </button>
        <button
          type="button"
          onClick={() => onDeposit(b)}
          className="cursor-pointer border border-rifle px-5 py-3 text-sm font-semibold text-rifle transition hover:bg-kangaroo active:scale-[0.97]"
        >
          Ask for deposit
        </button>
      </div>
      <p className="text-[13px] text-oyster-ink">
        Actual outcome (historical data, unknown at decision time):{' '}
        <b className={b.is_canceled ? 'text-rust' : 'text-rifle'}>{b.is_canceled ? 'cancelled' : 'not cancelled'}</b>
      </p>
    </aside>
  )
}

function BreakdownSection({
  state,
  metrics,
  metricsError,
}: {
  state: ApiState<Breakdowns>
  metrics: Record<string, Record<string, number>> | null
  metricsError: Error | null
}) {
  const [dim, setDim] = useState<(typeof DIMENSIONS)[number]['value']>('lead_time')
  const test = metrics?.test
  return (
    <Section
      title="Cancellation rate by group"
      aside={<Tabs label="Breakdown" options={DIMENSIONS} value={dim} onChange={setDim} />}
    >
      <div className="grid items-end gap-x-14 gap-y-6 md:grid-cols-[minmax(0,1fr)_auto]">
        <DataState state={state} minHeight={190}>
          {(d) => {
            const bd = d[dim as keyof Breakdowns]
            const items = dim === 'country' ? bd.items.filter((i) => i.bookings >= 500).slice(0, 8) : bd.items
            return (
              <ColumnBars
                columns={items.map((i) => ({
                  key: i.key,
                  label: dim === 'lead_time' ? `${i.label}d` : dim === 'country' ? i.key : i.label,
                  value: i.cancellation_rate,
                  title: `${i.label}: ${num(i.bookings)} bookings`,
                }))}
                max={1}
              />
            )
          }}
        </DataState>
        <div className="flex flex-col gap-4 pb-6">
          {metricsError ? (
            <ErrorBox error={metricsError} />
          ) : (
            <>
              <div className="flex flex-col gap-1.5">
                <Cap>Model AUC, 2017 test</Cap>
                <b className="font-display text-[64px] leading-[0.9] font-medium">
                  {test?.auc != null ? test.auc.toFixed(3) : '—'}
                </b>
              </div>
              <dl className="m-0 grid grid-cols-3 gap-4">
                {(
                  [
                    ['Precision', test?.precision],
                    ['Recall', test?.recall],
                    ['F1', test?.f1],
                  ] as [string, number | undefined][]
                ).map(([k, v]) => (
                  <div key={k}>
                    <dt>
                      <Cap>{k}</Cap>
                    </dt>
                    <dd className="mt-0.5 font-display text-[26px] font-medium tabular-nums">{pct(v ?? null, 0)}</dd>
                  </div>
                ))}
              </dl>
              <span className="text-[13px] text-oyster-ink">Precision/recall at the model's High threshold</span>
            </>
          )}
        </div>
      </div>
      {dim === 'country' && <Cap>Countries with ≥ 500 bookings, largest first</Cap>}
    </Section>
  )
}
