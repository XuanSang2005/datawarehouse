// KPI overview (G1) — user: General Manager.
// Decisions supported: track revenue, room-nights, ADR, cancellation rate; compare City and Resort; see seasonality.
// Every rate/ADR is computed from totals by the backend (rule 8); this page only displays them.
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ReferenceDot } from 'recharts'
import {
  getChannelRanking,
  getKpiSummary,
  getKpiTimeseries,
  getMarketRanking,
  type FilterParams,
} from '../api/endpoints'
import LedgerLineChart, { TipRow, type ChartRow } from '../components/charts/LedgerLineChart'
import DataState from '../components/common/DataState'
import {
  BarCell,
  BigNumber,
  Cap,
  Focal,
  KpiStrip,
  Legend,
  Money,
  Section,
  Tabs,
  td,
  th,
} from '../components/common/ledger'
import FilterBar from '../components/filters/FilterBar'
import { useFilters } from '../context/filters'
import { useApi, type ApiState } from '../hooks/useApi'
import { addDays, compact, eur, eurCompact, num, num1, pct } from '../lib/format'
import { COLORS, FONT_UI, hotelColor } from '../lib/theme'
import type { Grain, KpiPoint, KpiSummary, KpiValues } from '../types/api'

type Metric = 'adr' | 'realized_revenue' | 'room_nights_sold' | 'cancellation_rate'

const METRICS: { value: Metric; label: string; title: string; format: (v: number) => string }[] = [
  { value: 'adr', label: 'ADR', title: 'ADR', format: (v) => eur(v) },
  { value: 'realized_revenue', label: 'Revenue', title: 'Revenue', format: (v) => eurCompact(v) },
  { value: 'room_nights_sold', label: 'Room-nights', title: 'Room-nights', format: (v) => compact(v) },
  { value: 'cancellation_rate', label: 'Cancellation rate', title: 'Cancellation rate', format: (v) => pct(v, 0) },
]

const GRAINS: { value: Grain; label: string; title: string }[] = [
  { value: 'year', label: 'Year', title: 'by year' },
  { value: 'quarter', label: 'Quarter', title: 'by quarter' },
  { value: 'month', label: 'Month', title: 'by month' },
  { value: 'week', label: 'Week', title: 'by week' },
]
const NEXT_GRAIN: Partial<Record<Grain, Grain>> = { year: 'quarter', quarter: 'month', month: 'week' }

const PHOTO: Record<string, { src: string; alt: string; place: string }> = {
  both: { src: '/img/lisbon-tram.jpg', alt: 'Tram on a Lisbon street', place: 'Lisbon & Algarve' },
  City: { src: '/img/lisbon-aerial.jpg', alt: 'Lisbon rooftops by the river', place: 'Lisbon' },
  Resort: { src: '/img/coast-cliffs.jpg', alt: 'Algarve cliffs by the sea', place: 'Algarve' },
}

interface Drill {
  label: string
  from: string
  to: string
  grain: Grain
}

/** Last day of the period that starts at `start` (ISO) for the given grain. */
function periodEnd(start: string, grain: Grain): string {
  const d = new Date(`${start}T00:00:00Z`)
  if (grain === 'week') return addDays(start, 6)
  const months = grain === 'year' ? 12 : grain === 'quarter' ? 3 : 1
  d.setUTCMonth(d.getUTCMonth() + months)
  return addDays(d.toISOString().slice(0, 10), -1)
}

const maxIso = (a: string | null | undefined, b: string) => (a && a > b ? a : b)
const minIso = (a: string | null | undefined, b: string) => (a && a < b ? a : b)

export default function OverviewPage() {
  const { params, hotel, filters } = useFilters()
  const key = JSON.stringify(params)
  const summary = useApi(() => getKpiSummary(params), [key])

  return (
    <>
      <Hero summary={summary.data?.total ?? null} hotelType={hotel?.hotel_type ?? null} />
      <FilterBar />
      <DataState state={summary} minHeight={110}>
        {(s) => (
          <KpiStrip
            items={[
              { label: 'Realized revenue', value: <Money value={s.total.realized_revenue} compactForm /> },
              { label: 'Room-nights', value: compact(s.total.room_nights_sold) },
              { label: 'ADR', value: <Money value={s.total.adr} /> },
              { label: 'Cancellation rate', value: pct(s.total.cancellation_rate), alert: true },
            ]}
          />
        )}
      </DataState>
      <HotelComparison state={summary} />
      <TrendSection params={params} byHotel={filters.hotelKey == null} hotelType={hotel?.hotel_type ?? null} />
      <ChannelMix params={params} />
    </>
  )
}

function Hero({ summary, hotelType }: { summary: KpiValues | null; hotelType: string | null }) {
  const photo = PHOTO[hotelType ?? 'both'] ?? PHOTO.both
  const booked = summary ? summary.lost_revenue + summary.realized_revenue : null
  return (
    <div className="grid animate-rise md:min-h-[470px] md:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
      <Focal className="flex flex-col justify-between gap-10 px-[22px] py-[22px] [container-type:inline-size] sm:px-[34px] sm:pt-[30px] sm:pb-[34px]">
        <Cap className="text-kangaroo">Lost to cancellations before arrival</Cap>
        <div>
          <BigNumber className="text-[min(30cqi,176px)]">
            {summary ? <Money value={summary.lost_revenue} compactForm /> : '—'}
          </BigNumber>
          <p className="mt-[22px] text-[17px] text-kangaroo">
            <b className="font-semibold text-merino">{booked ? pct(summary!.lost_revenue / booked, 0) : '—'}</b> of
            booked room revenue · <b className="font-semibold text-merino">{eurCompact(summary?.net_lost_revenue)}</b>{' '}
            net of retained deposits
          </p>
        </div>
      </Focal>
      <div className="relative min-h-60 overflow-hidden bg-kangaroo">
        {Object.entries(PHOTO).map(([k, p]) => (
          <img
            key={k}
            src={p.src}
            alt={p.alt}
            loading={k === 'both' ? 'eager' : 'lazy'}
            className={`absolute inset-0 size-full object-cover [filter:sepia(.3)_saturate(.72)_contrast(.95)_brightness(.97)] transition-[opacity,transform] duration-1000 ease-ledger ${
              p === photo ? 'scale-100 opacity-100' : 'scale-105 opacity-0'
            }`}
          />
        ))}
        <Cap className="absolute right-0 bottom-0 z-10 bg-merino px-3.5 py-2">{photo.place}</Cap>
      </div>
    </div>
  )
}

function HotelComparison({ state }: { state: ApiState<KpiSummary> }) {
  return (
    <Section title="City and Resort">
      <DataState state={state} isEmpty={(s) => s.by_hotel.length === 0}>
        {(s) => (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-[14.5px]">
              <thead>
                <tr>
                  <th className={th}>Hotel</th>
                  <th className={`${th} text-right`}>Bookings</th>
                  <th className={`${th} text-right`}>Realized revenue</th>
                  <th className={`${th} text-right`}>Room-nights</th>
                  <th className={`${th} text-right`}>ADR</th>
                  <th className={th}>Cancellation rate</th>
                  <th className={`${th} text-right`}>Avg lead time</th>
                  <th className={`${th} text-right`}>Avg nights</th>
                </tr>
              </thead>
              <tbody>
                {s.by_hotel.map((h) => (
                  <tr key={h.hotel_key}>
                    <td className={td}>
                      <i
                        className="mr-2 inline-block size-2 align-[1px]"
                        style={{ background: hotelColor(h.hotel_name.split(' ')[0]) }}
                      />
                      <span className="font-semibold">{h.hotel_name}</span>
                    </td>
                    <td className={`${td} text-right font-mono tabular-nums`}>{num(h.bookings)}</td>
                    <td className={`${td} text-right font-mono tabular-nums`}>{eurCompact(h.realized_revenue)}</td>
                    <td className={`${td} text-right font-mono tabular-nums`}>{num(h.room_nights_sold)}</td>
                    <td className={`${td} text-right font-mono tabular-nums`}>{eur(h.adr)}</td>
                    <td className={td}>
                      <BarCell value={h.cancellation_rate} tone="rust" />
                    </td>
                    <td className={`${td} text-right font-mono tabular-nums`}>{num(h.avg_lead_time)} days</td>
                    <td className={`${td} text-right font-mono tabular-nums`}>{num1(h.avg_los)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </DataState>
    </Section>
  )
}

function TrendSection({
  params,
  byHotel,
  hotelType,
}: {
  params: FilterParams
  byHotel: boolean
  hotelType: string | null
}) {
  const [metric, setMetric] = useState<Metric>('adr')
  const [path, setPath] = useState<Drill[]>([])
  const drill = path[path.length - 1]
  const [baseGrain, setBaseGrain] = useState<Grain>('month')
  const activeGrain: Grain = drill?.grain ?? baseGrain

  // Drill-down narrows the chart's date range (intersected with the shared filters)
  const chartParams: FilterParams = drill
    ? { ...params, date_from: maxIso(params.date_from, drill.from), date_to: minIso(params.date_to, drill.to) }
    : params
  const key = JSON.stringify([chartParams, activeGrain, byHotel])
  const ts = useApi(() => getKpiTimeseries(activeGrain, chartParams, byHotel), [key])

  const m = METRICS.find((x) => x.value === metric)!
  const hotels = useMemo(() => {
    const seen = new Map<number, string>()
    ts.data?.points.forEach((p) => p.hotel_key != null && seen.set(p.hotel_key, p.hotel_name ?? ''))
    return [...seen.entries()]
  }, [ts.data])

  const rows: ChartRow[] = useMemo(() => {
    const byPeriod = new Map<string, ChartRow>()
    ts.data?.points.forEach((p: KpiPoint) => {
      const row = byPeriod.get(p.period) ?? { period: p.period, period_start: p.period_start }
      row[byHotel ? `h${p.hotel_key}` : 'all'] = p[metric]
      byPeriod.set(p.period, row)
    })
    return [...byPeriod.values()]
  }, [ts.data, metric, byHotel])

  const series = useMemo(
    () =>
      byHotel
        ? hotels.map(([k, name], i) => ({
            key: `h${k}`,
            name: name.replace(' Hotel', ''),
            color: hotelColor(name.split(' ')[0]),
            endLabel: true,
            labelDy: hotels.length > 1 ? (i === 0 ? -6 : 10) : 0,
          }))
        : [{ key: 'all', name: hotelType ?? 'Total', color: hotelColor(hotelType), endLabel: true }],
    [byHotel, hotels, hotelType],
  )

  // Highest point, annotated as in the prototype ("€174 in August")
  const peak = useMemo(() => {
    let best: { period: string; value: number; key: string; name: string } | null = null
    for (const r of rows)
      for (const s of series) {
        const v = r[s.key]
        if (typeof v === 'number' && (!best || v > best.value)) best = { period: String(r.period), value: v, key: s.key, name: s.name }
      }
    return best
  }, [rows, series])

  const nextGrain = NEXT_GRAIN[activeGrain]
  const onPointClick = nextGrain
    ? (row: ChartRow) => {
        const start = String(row.period_start)
        setPath((p) => [...p, { label: String(row.period), from: start, to: periodEnd(start, activeGrain), grain: nextGrain }])
      }
    : undefined

  return (
    <Section
      title={`${m.title} ${GRAINS.find((g) => g.value === activeGrain)?.title}`}
      aside={<Tabs label="Metric" options={METRICS} value={metric} onChange={setMetric} />}
    >
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
        <nav aria-label="Drill-down" className="flex flex-wrap items-center gap-2 font-mono text-[12px] tracking-[0.08em] uppercase">
          <button
            type="button"
            onClick={() => setPath([])}
            className={`cursor-pointer ${path.length ? 'text-oyster-ink underline underline-offset-4 hover:text-cedar' : 'text-cedar'}`}
          >
            All periods
          </button>
          {path.map((d, i) => (
            <span key={d.label} className="flex items-center gap-2">
              <span className="text-oyster">›</span>
              <button
                type="button"
                onClick={() => setPath((p) => p.slice(0, i + 1))}
                className={`cursor-pointer ${i < path.length - 1 ? 'text-oyster-ink underline underline-offset-4 hover:text-cedar' : 'text-cedar'}`}
              >
                {d.label}
              </button>
            </span>
          ))}
          {nextGrain && <span className="ml-2 normal-case tracking-normal text-oyster-ink">· click a point to drill down</span>}
        </nav>
        {!drill && (
          <Tabs label="Time grain" options={GRAINS} value={baseGrain} onChange={setBaseGrain} />
        )}
      </div>
      {byHotel && series.length > 1 && <Legend items={series.map((s) => ({ label: s.name, color: s.color }))} />}
      <DataState state={ts} minHeight={300} isEmpty={(d) => d.points.length === 0}>
        {() => (
          <LedgerLineChart
            label={`${m.title} by period`}
            data={rows}
            xKey="period"
            series={series}
            yFormat={m.format}
            yDomain={metric === 'cancellation_rate' || metric === 'adr' ? [0, 'auto'] : ['auto', 'auto']}
            onPointClick={onPointClick}
            tooltip={(row) => (
              <>
                <b className="font-semibold">{String(row.period)}</b>
                {series.map((s) => (
                  <TipRow key={s.key} label={s.name} color={s.color} value={typeof row[s.key] === 'number' ? m.format(row[s.key] as number) : '—'} />
                ))}
              </>
            )}
          >
            {peak && rows.length > 2 && (
              <ReferenceDot
                x={peak.period}
                y={peak.value}
                r={7}
                fill="none"
                stroke={COLORS.cedar}
                strokeWidth={1.25}
                label={{
                  value: `${m.format(peak.value)} · ${peak.period}`,
                  position: 'top',
                  offset: 12,
                  fill: COLORS.cedar,
                  fontFamily: FONT_UI,
                  fontSize: 14,
                  fontWeight: 600,
                }}
              />
            )}
          </LedgerLineChart>
        )}
      </DataState>
    </Section>
  )
}

function ChannelMix({ params }: { params: FilterParams }) {
  const [by, setBy] = useState<'channel' | 'market'>('channel')
  const key = JSON.stringify([params, by])
  const ranking = useApi(
    () => (by === 'channel' ? getChannelRanking({ ...params, top_n: 6 }) : getMarketRanking({ ...params, top_n: 6 })),
    [key],
  )
  return (
    <Section
      title="Sales channels"
      aside={
        <div className="flex items-baseline gap-6">
          <Tabs
            label="Group by"
            options={[
              { value: 'channel', label: 'Channel' },
              { value: 'market', label: 'Market' },
            ]}
            value={by}
            onChange={setBy}
          />
          <Link to="/channels" className="text-sm font-semibold text-rifle underline underline-offset-4">
            See full ranking →
          </Link>
        </div>
      }
    >
      <DataState state={ranking} isEmpty={(r) => r.items.length === 0}>
        {(r) => {
          const maxShare = Math.max(...r.items.map((i) => i.revenue_share ?? 0))
          return (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-[14.5px]">
                <thead>
                  <tr>
                    <th className={th}>{by === 'channel' ? 'Channel' : 'Market'}</th>
                    <th className={th}>Revenue share</th>
                    <th className={`${th} text-right`}>ADR</th>
                    <th className={th}>Cancellation rate</th>
                    <th className={`${th} text-right`}>Realized revenue</th>
                  </tr>
                </thead>
                <tbody>
                  {r.items.map((i) => (
                    <tr key={i.key}>
                      <td className={`${td} font-semibold`}>{i.label}</td>
                      <td className={td}>
                        <BarCell value={i.revenue_share} max={maxShare} />
                      </td>
                      <td className={`${td} text-right font-mono tabular-nums`}>{eur(i.adr)}</td>
                      <td className={td}>
                        <BarCell value={i.cancellation_rate} tone="rust" />
                      </td>
                      <td className={`${td} text-right font-mono tabular-nums`}>{eurCompact(i.realized_revenue)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        }}
      </DataState>
    </Section>
  )
}
