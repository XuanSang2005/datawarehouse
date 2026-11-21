// Mô phỏng What-if (G4) — người dùng: Revenue Manager.
// Quyết định hỗ trợ: nên overbooking bao nhiêu %, có nên đòi cọc booking rủi ro cao không.
// Toàn bộ phép tính ở backend (POST /api/what-if, công thức: backend/app/services/what_if_service.py).
// Frontend chỉ gửi tham số người dùng nhập (công suất, chi phí không có trong dataset — quy tắc 10) và hiển thị.
import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import { Area, ReferenceDot } from 'recharts'
import { runWhatIf } from '../api/endpoints'
import LedgerLineChart, { TipRow, type ChartRow } from '../components/charts/LedgerLineChart'
import DataState from '../components/common/DataState'
import { BigNumber, Cap, Focal, Money, PageHead, Section, Segmented, td } from '../components/common/ledger'
import { useFilters } from '../context/filters'
import { useApi, useDebounced } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { dateLabel, eur, num, num1, pct } from '../lib/format'

/** +€1.234 / −€1.234 / €0 */
const signedEur = (v: number) => `${v < 0 ? '−' : v > 0 ? '+' : ''}${eur(Math.abs(v))}`
import { COLORS, FONT_UI } from '../lib/theme'
import type { WhatIfRequest, WhatIfResponse } from '../types/api'

interface Inputs {
  capacity: number
  overbooking: number
  walkCost: number
  otaCommission: number
  threshold: number | null
  attrition: number
  deposit: boolean
}

function Slider({
  id,
  label,
  value,
  display,
  min,
  max,
  step,
  onChange,
  note,
}: {
  id: string
  label: string
  value: number
  display: string
  min: number
  max: number
  step: number
  onChange: (v: number) => void
  note?: string
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between gap-2.5">
        <label htmlFor={id} className="text-[14.5px] font-semibold">
          {label}
        </label>
        <output htmlFor={id} className="font-mono text-sm tabular-nums">
          {display}
        </output>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="range-ledger"
        style={{ '--p': `${((value - min) / (max - min)) * 100}%` } as CSSProperties}
      />
      {note && <Cap>{note}</Cap>}
    </div>
  )
}

const roundUp = (v: number, step: number) => Math.ceil(v / step) * step

export default function WhatIfPage() {
  const { options, filters } = useFilters()
  const hotels = options?.hotels ?? []
  const [localHotel, setLocalHotel] = useState<number | null>(null)
  const hotelKey = filters.hotelKey ?? localHotel ?? hotels[0]?.hotel_key ?? null
  const hotel = hotels.find((h) => h.hotel_key === hotelKey)
  const peak = hotel?.peak_rooms_occupied ?? 200

  const [inputs, setInputs] = useState<Inputs | null>(null)
  const [toast, showToast] = useToast()

  // Khởi tạo / đổi khách sạn: công suất mặc định = đêm đông nhất thực tế + 5%
  useEffect(() => {
    if (!hotel) return
    setInputs((cur) => ({
      overbooking: cur?.overbooking ?? 0.05,
      walkCost: cur?.walkCost ?? 150,
      otaCommission: cur?.otaCommission ?? 0.15,
      threshold: cur?.threshold ?? null,
      attrition: cur?.attrition ?? 0.05,
      deposit: cur?.deposit ?? true,
      capacity: roundUp((hotel.peak_rooms_occupied ?? 200) * 1.05, 5),
    }))
  }, [hotel])

  const request: WhatIfRequest | null =
    inputs && hotelKey
      ? {
          hotel_key: hotelKey,
          capacity: inputs.capacity,
          overbooking_pct: inputs.overbooking,
          walk_cost: inputs.walkCost,
          ota_commission: inputs.otaCommission,
          deposit_risk_threshold: inputs.threshold,
          deposit_attrition_pct: inputs.attrition,
        }
      : null
  const debounced = useDebounced(request, 300)
  const key = JSON.stringify(debounced)
  const result = useApi<WhatIfResponse | null>(
    () => (debounced ? runWhatIf(debounced) : Promise.resolve(null)),
    [key],
  )
  const r = result.data
  const set = (patch: Partial<Inputs>) => setInputs((cur) => (cur ? { ...cur, ...patch } : cur))

  const total = r ? r.overbooking.net_benefit + (inputs?.deposit && r.deposit ? r.deposit.net_benefit : 0) : null
  const perNight = r && total != null && r.baseline.nights ? total / r.baseline.nights : null
  const threshold = inputs?.threshold ?? r?.assumptions.deposit_risk_threshold ?? 0.31

  return (
    <>
      <PageHead
        title="Overbooking đến mức nào?"
        aside={
          filters.hotelKey == null && hotels.length > 0 ? (
            <Segmented<number | null>
              label="Khách sạn mô phỏng"
              value={hotelKey}
              onChange={setLocalHotel}
              options={hotels.map((h) => ({ value: h.hotel_key, label: h.hotel_name }))}
            />
          ) : undefined
        }
      />

      <div className="grid items-start gap-12 animate-rise lg:grid-cols-[minmax(0,330px)_minmax(0,1fr)]">
        <div className="order-2 flex flex-col gap-6 lg:sticky lg:top-28 lg:order-none">
          {inputs ? (
            <>
              <Slider
                id="wi-cap"
                label="Số phòng mỗi đêm"
                value={inputs.capacity}
                display={num(inputs.capacity)}
                min={roundUp(peak * 0.6, 10)}
                max={roundUp(peak * 2, 10)}
                step={5}
                onChange={(v) => set({ capacity: v })}
                note={`Bạn nhập · dataset không có · đêm đông nhất ${num(peak)} phòng`}
              />
              <Slider
                id="wi-ob"
                label="Overbooking"
                value={inputs.overbooking * 100}
                display={pct(inputs.overbooking)}
                min={0}
                max={30}
                step={0.5}
                onChange={(v) => set({ overbooking: v / 100 })}
              />
              <Slider
                id="wi-walk"
                label="Chi phí mỗi đêm phải chuyển khách"
                value={inputs.walkCost}
                display={eur(inputs.walkCost)}
                min={50}
                max={600}
                step={10}
                onChange={(v) => set({ walkCost: v })}
              />
              <Slider
                id="wi-ota"
                label="Hoa hồng OTA"
                value={inputs.otaCommission * 100}
                display={pct(inputs.otaCommission, 0)}
                min={0}
                max={30}
                step={1}
                onChange={(v) => set({ otaCommission: v / 100 })}
              />
              <label htmlFor="wi-dep" className="flex cursor-pointer items-center justify-between gap-3.5 text-[14.5px] font-semibold">
                Đòi cọc khi rủi ro ≥ {pct(threshold, 0)}
                <input
                  id="wi-dep"
                  type="checkbox"
                  className="peer sr-only"
                  checked={inputs.deposit}
                  onChange={(e) => set({ deposit: e.target.checked })}
                />
                <i
                  aria-hidden
                  className="relative h-6 w-11 flex-none border border-cedar transition-colors after:absolute after:top-[3px] after:left-[3px] after:size-4 after:bg-cedar after:transition-transform after:duration-300 peer-checked:border-rifle peer-checked:bg-rifle peer-checked:after:translate-x-5 peer-checked:after:bg-merino peer-focus-visible:outline-2 peer-focus-visible:outline-offset-3 peer-focus-visible:outline-rifle"
                />
              </label>
              {inputs.deposit && (
                <>
                  <Slider
                    id="wi-thr"
                    label="Ngưỡng xác suất hủy để đòi cọc"
                    value={Math.round(threshold * 100)}
                    display={pct(threshold, 0)}
                    min={10}
                    max={90}
                    step={1}
                    onChange={(v) => set({ threshold: v / 100 })}
                  />
                  <Slider
                    id="wi-attr"
                    label="Khách bỏ đặt vì bị đòi cọc"
                    value={inputs.attrition * 100}
                    display={pct(inputs.attrition, 0)}
                    min={0}
                    max={30}
                    step={1}
                    onChange={(v) => set({ attrition: v / 100 })}
                  />
                </>
              )}
              <button
                type="button"
                disabled={!r}
                onClick={() => {
                  if (!r) return
                  set({ overbooking: r.recommended_overbooking_pct })
                  showToast(`Đã đặt overbooking ${pct(r.recommended_overbooking_pct)}`)
                }}
                className="cursor-pointer border border-rifle bg-rifle px-5 py-3 text-sm font-semibold text-merino transition hover:border-cedar hover:bg-cedar active:scale-[0.97] disabled:opacity-50"
              >
                Dùng mức tốt nhất{r ? ` (${pct(r.recommended_overbooking_pct)})` : ''}
              </button>
            </>
          ) : (
            <Cap>Đang tải danh mục khách sạn…</Cap>
          )}
        </div>

        <div className="flex min-w-0 flex-col gap-11">
          <Focal className="grid items-end gap-7 p-[22px] sm:p-[30px_34px] md:grid-cols-[minmax(0,1fr)_minmax(0,260px)]">
            <div>
              <Cap className="text-kangaroo">Lợi ích ròng mỗi đêm</Cap>
              <BigNumber className="mt-3.5 text-[clamp(64px,8.5vw,132px)]">
                {perNight != null ? <Money value={Math.round(perNight)} signed /> : '—'}
              </BigNumber>
              <p className="mt-[18px] text-[17px] text-kangaroo">
                {r && total != null ? (
                  <>
                    <b className="font-semibold text-merino">{signedEur(total)}</b>{' '}
                    trong {num(r.baseline.nights)} đêm ({dateLabel(r.assumptions.date_from)}–
                    {dateLabel(r.assumptions.date_to)})
                  </>
                ) : (
                  '—'
                )}
              </p>
            </div>
            <div className="flex flex-col">
              {(
                [
                  ['Lấp phòng sau overbooking', pct(r?.overbooking.occupancy_rate_after ?? null)],
                  ['Đêm phòng phải chuyển khách', num1(r?.overbooking.rooms_walked ?? null)],
                  ['Đêm có nguy cơ hết phòng', r ? `${r.overbooking.nights_at_risk}/${r.baseline.nights}` : '—'],
                ] as [string, string][]
              ).map(([k, v]) => (
                <div key={k} className="flex items-baseline justify-between gap-3 border-t border-merino/25 py-2.5">
                  <span className="text-sm text-kangaroo">{k}</span>
                  <b className="font-display text-[30px] font-medium tabular-nums">{v}</b>
                </div>
              ))}
            </div>
          </Focal>

          {result.error && <DataState state={result}>{() => null}</DataState>}
          {r && r.warnings.length > 0 && (
            <ul className="flex flex-col gap-1.5 border-l-2 border-brass pl-4 text-sm">
              {r.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          )}

          <Section title="Lợi ích theo mức overbooking">
            <DataState state={result} minHeight={280} isEmpty={(d) => !d}>
              {(d) => d && <CurveChart data={d} current={inputs?.overbooking ?? 0} />}
            </DataState>
          </Section>

          <Section title="Tách lợi ích">
            <DataState state={result} isEmpty={(d) => !d}>
              {(d) => d && <Breakdown data={d} depositOn={inputs?.deposit ?? false} total={total ?? 0} />}
            </DataState>
          </Section>
        </div>
      </div>
      {toast}
    </>
  )
}

function CurveChart({ data, current }: { data: WhatIfResponse; current: number }) {
  const rows: ChartRow[] = useMemo(
    () =>
      data.curve.map((c) => ({
        x: pct(c.overbooking_pct, 0),
        pct: c.overbooking_pct,
        net: c.net_benefit,
        pos: Math.max(0, c.net_benefit),
        neg: Math.min(0, c.net_benefit),
        walked: c.rooms_walked,
        risk: c.nights_at_risk,
      })),
    [data],
  )
  const best = rows.find((r) => r.pct === data.recommended_overbooking_pct)
  const cur = rows.reduce<ChartRow | null>(
    (a, r) => (!a || Math.abs(Number(r.pct) - current) < Math.abs(Number(a.pct) - current) ? r : a),
    null,
  )
  const money = (v: number) => `${v < 0 ? '−' : ''}€${num(Math.abs(v) / 1000)}K`
  return (
    <LedgerLineChart
      label="Lợi ích ròng theo mức overbooking"
      data={rows}
      xKey="x"
      series={[{ key: 'net', name: 'Lợi ích ròng', color: COLORS.rifle }]}
      height={280}
      zeroLine
      yFormat={money}
      tooltip={(row) => (
        <>
          <b className="font-semibold">Overbooking {String(row.x)}</b>
          <TipRow label="Lợi ích ròng" value={eur(Number(row.net))} />
          <TipRow label="Đêm phòng chuyển khách" value={num1(Number(row.walked))} />
          <TipRow label="Đêm có nguy cơ" value={String(row.risk)} />
        </>
      )}
    >
      <Area dataKey="pos" stroke="none" fill={COLORS.rifle} fillOpacity={0.12} isAnimationActive={false} activeDot={false} />
      <Area dataKey="neg" stroke="none" fill={COLORS.rust} fillOpacity={0.16} isAnimationActive={false} activeDot={false} />
      {best && (
        <ReferenceDot
          x={best.x as string}
          y={Number(best.net)}
          r={7}
          fill={COLORS.merino}
          stroke={COLORS.rifle}
          strokeWidth={2}
          label={{
            value: `Tốt nhất ${best.x}`,
            position: 'top',
            offset: 14,
            fill: COLORS.cedar,
            fontFamily: FONT_UI,
            fontSize: 13.5,
            fontWeight: 600,
          }}
        />
      )}
      {cur && cur !== best && (
        <ReferenceDot x={cur.x as string} y={Number(cur.net)} r={6} fill={COLORS.rifle} stroke={COLORS.merino} strokeWidth={2.5} />
      )}
    </LedgerLineChart>
  )
}

function Breakdown({ data, depositOn, total }: { data: WhatIfResponse; depositOn: boolean; total: number }) {
  const o = data.overbooking
  const d = data.deposit
  const b = data.baseline
  const rows: [string, number | null, string][] = [
    ['Doanh thu cứu được nhờ overbooking', o.revenue_recovered, `${num1(o.rooms_filled)} đêm phòng trống được lấp, sau hoa hồng OTA`],
    ['Chi phí chuyển khách', -o.walk_cost_total, `${num1(o.rooms_walked)} đêm phòng × ${eur(data.assumptions.walk_cost)}`],
  ]
  if (d && depositOn) {
    rows.push(
      ['Tiền cọc giữ lại', d.deposit_retained, `${num(d.flagged_bookings)} booking bị đòi cọc, ${pct(d.flagged_precision, 0)} trong đó thực tế hủy · cọc ${pct(d.deposit_rate, 0)}`],
      ['Mất do khách bỏ đặt', -d.attrition_loss, `${pct(d.attrition_pct, 0)} khách không hủy bỏ đặt vì bị đòi cọc`],
    )
  }
  return (
    <div className="flex flex-col gap-6">
      <table className="w-full border-collapse text-[14.5px]">
        <tbody>
          {rows.map(([label, v, note]) => (
            <tr key={label}>
              <td className="border-t border-kangaroo py-3.5 pr-3.5 align-middle">
                <span className="font-semibold">{label}</span>
                <span className="block text-[13px] text-oyster-ink">{note}</span>
              </td>
              <td className={`${td} text-right font-mono tabular-nums ${v != null && v < 0 ? 'text-rust' : ''}`}>
                {v == null ? '—' : signedEur(v)}
              </td>
            </tr>
          ))}
          <tr>
            <td className="border-t border-cedar py-3.5 font-semibold">Tổng lợi ích ròng</td>
            <td className={`border-t border-cedar py-3.5 text-right font-mono font-semibold tabular-nums ${total < 0 ? 'text-rust' : ''}`}>
              {signedEur(total)}
            </td>
          </tr>
        </tbody>
      </table>
      <div className="grid grid-cols-2 gap-y-5 sm:grid-cols-4">
        {(
          [
            ['Occupancy hiện tại', pct(b.occupancy_rate)],
            ['RevPAR hiện tại', eur(b.revpar)],
            ['ADR', eur(b.adr)],
            ['Tỉ trọng doanh thu OTA', pct(b.ota_revenue_share, 0)],
          ] as [string, string][]
        ).map(([k, v], i) => (
          <div key={k} className={`flex flex-col gap-1 ${i % 2 ? 'border-l border-kangaroo pl-5' : ''} ${i === 2 ? 'sm:border-l sm:border-kangaroo sm:pl-5' : ''}`}>
            <Cap>{k}</Cap>
            <b className="font-display text-[30px] font-medium tabular-nums">{v}</b>
          </div>
        ))}
      </div>
      <p className="text-[13px] text-oyster-ink">
        Occupancy và RevPAR tính theo số phòng bạn nhập. Giả định: chỉ nhận thêm đặt phòng ở đêm đã kín trên sổ; tỉ lệ
        hủy lấy theo thực tế từng đêm, nên rủi ro hết phòng có thể bị đánh giá thấp. Công thức chi tiết:{' '}
        <code className="font-mono">backend/app/services/what_if_service.py</code>.
      </p>
    </div>
  )
}
