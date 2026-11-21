// Dự báo nhu cầu (G3) — người dùng: Revenue Manager, Sales & Marketing Manager.
// Quyết định hỗ trợ: chuẩn bị nhân sự, giá, mức overbooking cho các tuần tới.
// Dữ liệu: gold.ml_demand_forecast (E4) + room-nights thực tế theo tuần (gold.kpi_weekly_occupancy).
import { useMemo, useState } from 'react'
import { getForecast, getForecastMetrics } from '../api/endpoints'
import LedgerLineChart, { TipRow, type BandSeries, type ChartRow, type LineSeries } from '../components/charts/LedgerLineChart'
import DataState from '../components/common/DataState'
import { BigNumber, Cap, Focal, Legend, PageHead, Section, Tabs, td, th } from '../components/common/ledger'
import { useFilters } from '../context/filters'
import { useApi } from '../hooks/useApi'
import { dayMonth, isoWeek, num, pct } from '../lib/format'
import { COLORS, hotelColor } from '../lib/theme'
import type { ForecastMetricsResponse, HotelForecast } from '../types/api'

type Range = '2017' | 'all'

const MODEL_LABEL: Record<string, string> = {
  forecast_gbm: 'Gradient Boosting (chính)',
  forecast_seasonal_naive: 'Cùng tuần năm trước',
  forecast_moving_avg: 'Trung bình 4 tuần',
}

const shortName = (s: HotelForecast) => s.hotel_name.replace(' Hotel', '')

export default function ForecastPage() {
  const { filters } = useFilters()
  const [range, setRange] = useState<Range>('2017')
  const forecast = useApi(() => getForecast(filters.hotelKey ?? undefined), [filters.hotelKey])
  const metrics = useApi(getForecastMetrics)

  const series = useMemo(() => forecast.data?.series ?? [], [forecast.data])

  // 8 tuần tương lai: cộng dự báo các khách sạn đang chọn (tổng kỳ vọng cộng được)
  const future = useMemo(() => {
    const weeks = new Map<string, { week: string; total: number; perHotel: { name: string; p: number; lo: number; hi: number }[] }>()
    series.forEach((s) =>
      s.points
        .filter((p) => p.is_future)
        .forEach((p) => {
          const w = weeks.get(p.week_start_date) ?? { week: p.week_start_date, total: 0, perHotel: [] }
          w.total += p.predicted_room_nights
          w.perHotel.push({ name: shortName(s), p: p.predicted_room_nights, lo: p.lower_bound, hi: p.upper_bound })
          weeks.set(p.week_start_date, w)
        }),
    )
    return [...weeks.values()].sort((a, b) => a.week.localeCompare(b.week))
  }, [series])
  const peak = future.reduce<(typeof future)[number] | null>((best, w) => (!best || w.total > best.total ? w : best), null)

  const { rows, lines, bands, forecastFrom, forecastTo } = useMemo(() => buildChart(series, range), [series, range])

  return (
    <>
      <div className="grid items-stretch gap-x-12 gap-y-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,440px)]">
        <PageHead title={<>Room-nights,<br />8 tuần tới</>} />
        <Focal className="flex flex-col justify-between gap-[18px] px-[22px] py-[22px] sm:px-7 sm:py-6">
          <Cap className="text-kangaroo">Tuần bận nhất sắp tới</Cap>
          <div>
            <BigNumber className="text-[clamp(64px,7vw,108px)]">{peak ? num(peak.total) : '—'}</BigNumber>
            <p className="mt-3.5 text-[17px] text-kangaroo">
              {peak ? (
                <>
                  <b className="font-semibold text-merino">Tuần {isoWeek(peak.week)}</b> · từ {dayMonth(peak.week)}
                  {peak.perHotel.length === 1 &&
                    ` · khoảng ${num(peak.perHotel[0].lo)}–${num(peak.perHotel[0].hi)}`}
                </>
              ) : (
                '—'
              )}
            </p>
          </div>
        </Focal>
      </div>

      <Section
        title={range === '2017' ? 'Room-nights theo tuần, 2017' : 'Room-nights theo tuần, 2015–2017'}
        aside={
          <Tabs
            label="Khoảng thời gian"
            value={range}
            onChange={setRange}
            options={[
              { value: '2017', label: '2017' },
              { value: 'all', label: 'Toàn bộ' },
            ]}
          />
        }
      >
        <Legend
          items={[
            ...series.map((s) => ({ label: `${shortName(s)} thực tế`, color: hotelColor(shortName(s)) })),
            { label: 'Dự báo', color: COLORS.cedar, dashed: true },
            { label: 'Khoảng 80%', color: COLORS.cedar, box: true },
          ]}
        />
        <DataState state={forecast} minHeight={340} isEmpty={(d) => d.series.length === 0}>
          {() => (
            <LedgerLineChart
              label="Room-nights theo tuần: thực tế và dự báo"
              data={rows}
              xKey="week"
              xFormat={(w) => `T${isoWeek(w)}`}
              series={lines}
              bands={bands}
              height={340}
              yFormat={(v) => num(v)}
              highlight={forecastFrom && forecastTo ? { from: forecastFrom, to: forecastTo, label: 'Dự báo' } : undefined}
              tooltip={(row) => (
                <>
                  <b className="font-semibold">
                    Tuần {isoWeek(String(row.week))} · {dayMonth(String(row.week))}
                  </b>
                  {series.map((s) => {
                    const k = s.hotel_key
                    const a = row[`a${k}`]
                    const f = row[`f${k}`] ?? row[`bt${k}`]
                    const b = row[`b${k}`] as [number, number] | undefined
                    const c = hotelColor(shortName(s))
                    return (
                      <div key={k} className="mt-1">
                        {series.length > 1 && <span className="text-kangaroo">{shortName(s)}</span>}
                        {typeof a === 'number' && <TipRow label="Thực tế" value={num(a)} color={c} />}
                        {typeof f === 'number' && <TipRow label="Dự báo" value={num(f)} />}
                        {b && <TipRow label="Khoảng" value={`${num(b[0])}–${num(b[1])}`} />}
                      </div>
                    )
                  })}
                </>
              )}
            />
          )}
        </DataState>
        <span className="text-[13px] text-oyster-ink">
          Nét đứt mảnh trong 2017 là dự báo backtest 1 tuần trước (model chỉ dùng dữ liệu đến tuần trước đó), để so
          với thực tế.
        </span>
      </Section>

      <Section title="Từng tuần" aside={<MapeCaption metrics={metrics.data} hotelName={series.length === 1 ? series[0].hotel_name : null} />}>
        <div className="overflow-x-auto">
          <div className="grid min-w-[760px] grid-cols-8">
            {future.map((w, i) => (
              <div
                key={w.week}
                className={`flex flex-col gap-1 px-3.5 pt-3.5 pb-4 transition-colors ${
                  w === peak ? 'bg-kangaroo' : i === 0 ? 'pl-0' : 'border-l border-kangaroo'
                }`}
              >
                <small className="font-mono text-[11.5px] text-oyster-ink">
                  T{isoWeek(w.week)} · {dayMonth(w.week)}
                </small>
                <b className="font-display text-[30px] leading-[1.05] font-medium tabular-nums">{num(w.total)}</b>
                {w.perHotel.length === 1 ? (
                  <small className="font-mono text-[11.5px] text-oyster-ink">
                    {num(w.perHotel[0].lo)}–{num(w.perHotel[0].hi)}
                  </small>
                ) : (
                  w.perHotel.map((h) => (
                    <small key={h.name} className="font-mono text-[11.5px] text-oyster-ink">
                      {h.name} {num(h.p)}
                    </small>
                  ))
                )}
              </div>
            ))}
          </div>
        </div>
      </Section>

      <Section title="Sai số theo số tuần dự báo trước">
        <DataState state={metrics} isEmpty={(m) => m.models.length === 0}>
          {(m) => <MapeTable metrics={m} />}
        </DataState>
      </Section>
    </>
  )
}

function buildChart(series: HotelForecast[], range: Range) {
  const rows = new Map<string, ChartRow>()
  const get = (w: string) => {
    const r = rows.get(w) ?? { week: w }
    rows.set(w, r)
    return r
  }
  let forecastFrom: string | null = null
  let forecastTo: string | null = null
  series.forEach((s) => {
    const k = s.hotel_key
    s.history.forEach((h) => (get(h.week_start_date)[`a${k}`] = h.room_nights_sold))
    const lastActual = s.history[s.history.length - 1]
    s.points.forEach((p) => {
      const r = get(p.week_start_date)
      if (p.is_future) {
        r[`f${k}`] = p.predicted_room_nights
        r[`b${k}`] = [p.lower_bound, p.upper_bound]
        if (!forecastFrom || p.week_start_date < forecastFrom) forecastFrom = p.week_start_date
        if (!forecastTo || p.week_start_date > forecastTo) forecastTo = p.week_start_date
      } else {
        r[`bt${k}`] = p.predicted_room_nights
      }
    })
    // Nối đường dự báo với tuần thực tế cuối cùng (như prototype)
    if (lastActual) {
      const r = get(lastActual.week_start_date)
      r[`f${k}`] = lastActual.room_nights_sold
      r[`b${k}`] = [lastActual.room_nights_sold, lastActual.room_nights_sold]
    }
  })
  let data = [...rows.values()].sort((a, b) => String(a.week).localeCompare(String(b.week)))
  if (range === '2017') data = data.filter((r) => String(r.week) >= '2017-01-01')

  const lines: LineSeries[] = []
  const bands: BandSeries[] = []
  series.forEach((s, i) => {
    const k = s.hotel_key
    const color = hotelColor(shortName(s))
    const name = shortName(s)
    lines.push({ key: `a${k}`, name, color, endLabel: false })
    lines.push({ key: `bt${k}`, name: `${name} backtest`, color, dashed: true, width: 1.25 })
    lines.push({ key: `f${k}`, name, color, dashed: true, endLabel: true, labelDy: series.length > 1 ? (i === 0 ? -6 : 10) : 0 })
    bands.push({ key: `b${k}`, color })
  })
  return { rows: data, lines, bands, forecastFrom, forecastTo }
}

function MapeCaption({ metrics, hotelName }: { metrics: ForecastMetricsResponse | null; hotelName: string | null }) {
  if (!metrics) return null
  const suffix = hotelName ? `_${hotelName.toLowerCase().replace(' ', '_')}` : ''
  const get = (name: string) => metrics.models.find((m) => m.model_name === name)?.metrics.backtest?.[`mape${suffix}`]
  return (
    <Cap>
      MAPE backtest {pct(get('forecast_gbm') ?? null)} · cùng tuần năm trước {pct(get('forecast_seasonal_naive') ?? null)}
    </Cap>
  )
}

function MapeTable({ metrics }: { metrics: ForecastMetricsResponse }) {
  const hs = [1, 2, 3, 4, 5, 6, 7, 8]
  const models = [...metrics.models].sort((a, b) => (a.model_name === 'forecast_gbm' ? -1 : b.model_name === 'forecast_gbm' ? 1 : 0))
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-[14.5px]">
        <thead>
          <tr>
            <th className={th}>Model</th>
            {hs.map((h) => (
              <th key={h} className={`${th} text-right`}>
                {h} tuần
              </th>
            ))}
            <th className={`${th} text-right`}>Chung</th>
            <th className={`${th} text-right`}>Độ phủ 80%</th>
          </tr>
        </thead>
        <tbody>
          {models.map((m) => {
            const bt = m.metrics.backtest ?? {}
            const main = m.model_name === 'forecast_gbm'
            return (
              <tr key={m.model_name}>
                <td className={`${td} ${main ? 'font-semibold' : ''}`}>{MODEL_LABEL[m.model_name] ?? m.model_name}</td>
                {hs.map((h) => (
                  <td key={h} className={`${td} text-right font-mono tabular-nums`}>
                    {pct(bt[`mape_h${h}`] ?? null)}
                  </td>
                ))}
                <td className={`${td} text-right font-mono font-semibold tabular-nums`}>{pct(bt.mape ?? null)}</td>
                <td className={`${td} text-right font-mono tabular-nums`}>{pct(bt.interval_coverage_80 ?? null, 0)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="mt-3 text-[13px] text-oyster-ink">
        MAPE = trung bình |thực tế − dự báo| / thực tế trên backtest rolling-origin các tuần 2017. Càng thấp càng tốt.
      </p>
    </div>
  )
}
