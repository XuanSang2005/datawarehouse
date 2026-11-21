// Rủi ro hủy phòng (G2) — người dùng: Revenue Manager, bộ phận Reservations.
// Quyết định hỗ trợ: tuần này gọi xác nhận / yêu cầu cọc những booking nào; nhóm khách nào hủy nhiều.
// Điểm rủi ro lấy từ gold.ml_booking_risk (model dự đoán hủy, E3); mặc định chỉ booking năm 2017 (ngoài mẫu).
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

// Tập test của model: booking đến năm 2017 (dữ liệu kết thúc 31/8/2017)
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
/** Nhóm lead time — PHẢI khớp backend (repositories/booking_sql.py). */
function leadBand(lead: number): string {
  return LEAD_BANDS.find(([max]) => lead <= max)?.[1] ?? '>365'
}

const DIMENSIONS: { value: BreakdownDimension; label: string }[] = [
  { value: 'lead_time', label: 'Đặt trước' },
  { value: 'channel', label: 'Kênh' },
  { value: 'deposit_type', label: 'Đặt cọc' },
  { value: 'country', label: 'Quốc gia' },
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

  // Đổi bộ lọc → về trang đầu
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

  return (
    <>
      <PageHead
        title={`Khách đến ${dayMonth(week)}–${dateLabel(weekEnd)}`}
        aside={
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={!canPrev}
              onClick={() => setWeek((w) => addDays(w, -7))}
              className="cursor-pointer border border-cedar px-3.5 py-2 text-[13.5px] font-semibold hover:bg-kangaroo disabled:cursor-default disabled:opacity-40"
            >
              ← Tuần trước
            </button>
            <button
              type="button"
              disabled={!canNext}
              onClick={() => setWeek((w) => addDays(w, 7))}
              className="cursor-pointer border border-cedar px-3.5 py-2 text-[13.5px] font-semibold hover:bg-kangaroo disabled:cursor-default disabled:opacity-40"
            >
              Tuần sau →
            </button>
          </div>
        }
      />

      <Focal className="grid items-end gap-x-12 gap-y-5 p-[22px] sm:p-[28px_34px] md:grid-cols-[auto_minmax(0,1fr)] xl:grid-cols-[auto_minmax(0,1fr)_auto]">
        <div>
          <Cap className="text-kangaroo">Có khả năng hủy</Cap>
          <BigNumber className="text-[clamp(72px,9vw,132px)]">{list.data ? num(list.data.total) : '—'}</BigNumber>
        </div>
        <div className="flex flex-col gap-1.5 pb-2">
          <Cap className="text-kangaroo">Doanh thu phòng có nguy cơ mất</Cap>
          <b className="font-display text-[40px] leading-none font-medium tabular-nums">
            {list.data ? <Money value={list.data.expected_loss_total} /> : '—'}
          </b>
          <span className="text-sm text-kangaroo">
            kỳ vọng = Σ xác suất × doanh thu đặt · tổng đặt {list.data ? eur(list.data.booked_revenue_total) : '—'}
          </span>
        </div>
        <div className="flex min-w-0 flex-col gap-2 pb-2 md:col-span-2 xl:col-span-1 xl:min-w-[260px]">
          <label className="font-mono text-[11.5px] tracking-[0.14em] text-kangaroo uppercase" htmlFor="thr">
            Gắn cờ khi xác suất ≥
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
          <span className="text-[13px] text-kangaroo">Ngưỡng High của model: {pct(modelThreshold, 0)}</span>
        </div>
      </Focal>

      <FilterBar hide={['dates']} />

      <div className="grid items-start animate-rise xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <section className="flex min-w-0 flex-col gap-4 xl:pr-10">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <Cap>
              {list.data ? `${num(items.length)} / ${num(list.data.total)} booking · ${list.data.model_version}` : ' '}
            </Cap>
            <Tabs
              label="Sắp xếp"
              value={sort}
              onChange={setSort}
              options={[
                { value: 'probability', label: 'Xác suất hủy' },
                { value: 'expected_loss', label: 'Thiệt hại kỳ vọng' },
              ]}
            />
          </div>
          <DataState
            state={list}
            minHeight={420}
            isEmpty={(d) => d.items.length === 0}
            empty="Không có booking nào vượt ngưỡng trong tuần này. Thử hạ ngưỡng hoặc đổi tuần."
          >
            {(d) => (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-[14.5px]">
                  <thead>
                    <tr>
                      <th className={`${th} pl-2.5`}>Booking</th>
                      <th className={th}>Ngày đến</th>
                      <th className={`${th} text-right`}>Đêm</th>
                      <th className={th}>Kênh</th>
                      <th className={`${th} text-right`}>Đặt trước</th>
                      <th className={th}>Rủi ro</th>
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
                    Xem thêm {Math.min(PAGE_SIZE, d.total - items.length)} booking
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
          onCall={(b) => queue(b, 'Gọi', `#${b.booking_id} đã thêm vào danh sách gọi xác nhận hôm nay`)}
          onDeposit={(b) => queue(b, 'Cọc', `Đã soạn yêu cầu đặt cọc cho #${b.booking_id}`)}
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
  // Yếu tố = tỉ lệ hủy LỊCH SỬ của nhóm booking giống booking này, so với tỉ lệ chung (không phải giải thích của model)
  const factors: Factor[] = useMemo(() => {
    if (!b || !breakdowns) return []
    const find = (items: BreakdownItem[], key: string) => items.find((i) => i.key === key)?.cancellation_rate ?? null
    return [
      { label: `Đặt trước ${b.lead_time} ngày`, rate: find(breakdowns.lead_time.items, leadBand(b.lead_time)) },
      { label: `Đặt cọc: ${b.deposit_type}`, rate: find(breakdowns.deposit_type.items, b.deposit_type) },
      { label: `Kênh ${b.channel_group}`, rate: find(breakdowns.channel.items, b.channel_group) },
      { label: `Khách từ ${b.country_code}`, rate: find(breakdowns.country.items, b.country_code) },
    ]
  }, [b, breakdowns])

  if (!b) {
    return (
      <aside className="mt-8 border-t border-cedar pt-6 xl:mt-0 xl:border-t-0 xl:border-l xl:pt-0 xl:pl-10">
        <p className="text-oyster-ink">Chọn một booking để xem chi tiết.</p>
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
      <div className="relative h-1.5 bg-kangaroo" title={`Ngưỡng ${pct(threshold, 0)}`}>
        <i className="absolute inset-y-0 left-0 bg-rust" style={{ width: `${b.cancel_probability * 100}%` }} />
        <b className="absolute -top-[7px] -bottom-[7px] w-0.5 bg-cedar" style={{ left: `calc(${threshold * 100}% - 1px)` }} />
      </div>

      {factors.length > 0 && (
        <div className="flex flex-col gap-2.5">
          <Cap>Tỉ lệ hủy lịch sử của nhóm tương tự · chung {pct(overall, 0)}</Cap>
          {factors.map((f) => {
            const diff = f.rate != null && overall != null ? f.rate - overall : 0
            const width = Math.min(50, (Math.abs(diff) / 0.5) * 50)
            return (
              <div key={f.label} className="grid grid-cols-[minmax(0,1fr)_110px_44px] items-center gap-3.5 text-[14.5px]">
                <span className="truncate">{f.label}</span>
                <span
                  className="relative h-2 before:absolute before:-top-1 before:-bottom-1 before:left-1/2 before:w-px before:bg-cedar"
                  title={diff > 0 ? 'cao hơn tỉ lệ chung' : 'thấp hơn tỉ lệ chung'}
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
            ['Ngày đến', dayLabel(b.arrival_date)],
            ['Số đêm', b.total_nights],
            ['Đặt cọc', b.deposit_type],
            ['Phân khúc', b.market_segment],
            ['ADR', eur(b.adr)],
            ['Doanh thu', eur(b.booked_revenue)],
            ['Đặt ngày', dateLabel(b.booking_date)],
            ['Yêu cầu riêng', b.total_of_special_requests],
            ['Hủy trước đây', b.previous_cancellations],
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
          Gọi xác nhận lại
        </button>
        <button
          type="button"
          onClick={() => onDeposit(b)}
          className="cursor-pointer border border-rifle px-5 py-3 text-sm font-semibold text-rifle transition hover:bg-kangaroo active:scale-[0.97]"
        >
          Yêu cầu đặt cọc
        </button>
      </div>
      <p className="text-[13px] text-oyster-ink">
        Kết quả thực tế (dữ liệu lịch sử, lúc ra quyết định chưa biết):{' '}
        <b className={b.is_canceled ? 'text-rust' : 'text-rifle'}>{b.is_canceled ? 'đã hủy' : 'không hủy'}</b>
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
      title="Tỉ lệ hủy theo nhóm"
      aside={<Tabs label="Chiều phân tích" options={DIMENSIONS} value={dim} onChange={setDim} />}
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
                  title: `${i.label}: ${num(i.bookings)} booking`,
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
                <Cap>AUC model, tập test 2017</Cap>
                <b className="font-display text-[64px] leading-[0.9] font-medium">
                  {test?.auc != null ? test.auc.toFixed(3).replace('.', ',') : '—'}
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
              <span className="text-[13px] text-oyster-ink">Precision/recall tại ngưỡng High của model</span>
            </>
          )}
        </div>
      </div>
      {dim === 'country' && <Cap>Quốc gia có ≥ 500 booking, nhiều booking nhất</Cap>}
    </Section>
  )
}
