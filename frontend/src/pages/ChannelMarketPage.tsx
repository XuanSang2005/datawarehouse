// Kênh và thị trường (G5) — người dùng: Sales & Marketing Manager.
// Quyết định hỗ trợ: phân bổ ngân sách marketing / hợp đồng kênh vào kênh và quốc gia mang lại doanh thu thực
// (sau hủy) cao, ADR tốt, tỉ lệ hủy thấp. Dữ liệu: GET /api/channels/ranking, /api/markets/ranking.
import { useState } from 'react'
import { CartesianGrid, LabelList, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts'
import { getChannelRanking, getMarketRanking } from '../api/endpoints'
import { TipRow } from '../components/charts/LedgerLineChart'
import DataState from '../components/common/DataState'
import { BarCell, BigNumber, Cap, Focal, PageHead, Section, Segmented, Tabs, td, th } from '../components/common/ledger'
import FilterBar from '../components/filters/FilterBar'
import { useFilters } from '../context/filters'
import { useApi } from '../hooks/useApi'
import { eur, eurCompact, num, pct } from '../lib/format'
import { COLORS, FONT_MONO, FONT_UI } from '../lib/theme'
import type { RankingItem, RankingResponse, RankingSort } from '../types/api'

type Dimension = 'channel' | 'market'

const SORTS: { value: RankingSort; label: string }[] = [
  { value: 'realized_revenue', label: 'Doanh thu thực' },
  { value: 'adr', label: 'ADR' },
  { value: 'cancellation_rate', label: 'Hủy ít nhất' },
  { value: 'bookings', label: 'Số booking' },
]

export default function ChannelMarketPage() {
  const { params } = useFilters()
  const [dim, setDim] = useState<Dimension>('channel')
  const [sortBy, setSortBy] = useState<RankingSort>('realized_revenue')
  const [topN, setTopN] = useState(10)

  const key = JSON.stringify([params, dim, sortBy, topN])
  const ranking = useApi(
    () =>
      dim === 'channel'
        ? getChannelRanking({ ...params, sort_by: sortBy, top_n: topN })
        : getMarketRanking({ ...params, sort_by: sortBy, top_n: topN, min_bookings: 100 }),
    [key],
  )
  // Khối điểm nhấn luôn là kênh/thị trường doanh thu thực lớn nhất, không phụ thuộc cách sắp xếp
  const leaderKey = JSON.stringify([params, dim])
  const leader = useApi(
    () =>
      dim === 'channel'
        ? getChannelRanking({ ...params, sort_by: 'realized_revenue', top_n: 1 })
        : getMarketRanking({ ...params, sort_by: 'realized_revenue', top_n: 1, min_bookings: 100 }),
    [leaderKey],
  )
  const top = leader.data?.items[0]

  return (
    <>
      <div className="grid items-stretch gap-x-12 gap-y-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,480px)]">
        <PageHead
          title="Doanh thu thực đến từ đâu?"
          aside={
            <Segmented<Dimension>
              label="Xếp hạng theo"
              value={dim}
              onChange={setDim}
              options={[
                { value: 'channel', label: 'Kênh bán' },
                { value: 'market', label: 'Thị trường' },
              ]}
            />
          }
        />
        <Focal className="flex flex-col justify-between gap-[18px] px-[22px] py-[22px] sm:px-7 sm:py-6">
          <Cap className="text-kangaroo">{dim === 'channel' ? 'Kênh mang về nhiều nhất' : 'Thị trường lớn nhất'}</Cap>
          <div>
            <BigNumber className="text-[clamp(64px,7vw,108px)]">{top ? pct(top.revenue_share, 0) : '—'}</BigNumber>
            <p className="mt-3.5 text-[17px] text-kangaroo">
              {top ? (
                <>
                  doanh thu thực từ <b className="font-semibold text-merino">{top.label}</b> · ADR {eur(top.adr)} · hủy{' '}
                  {pct(top.cancellation_rate, 0)}
                </>
              ) : (
                '—'
              )}
            </p>
          </div>
        </Focal>
      </div>

      <FilterBar hide={dim === 'channel' ? ['channel'] : ['country']} />

      <Section
        title={dim === 'channel' ? 'Xếp hạng kênh bán' : 'Xếp hạng thị trường'}
        aside={
          <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
            <Tabs label="Sắp xếp theo" options={SORTS} value={sortBy} onChange={setSortBy} />
            <label className="flex items-baseline gap-2">
              <Cap>Top</Cap>
              <select
                value={topN}
                onChange={(e) => setTopN(Number(e.target.value))}
                className="cursor-pointer border-0 border-b border-cedar bg-transparent text-sm font-semibold"
              >
                {[5, 10, 20, 50].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
          </div>
        }
      >
        <DataState state={ranking} isEmpty={(r) => r.items.length === 0}>
          {(r) => <RankingTable data={r} />}
        </DataState>
      </Section>

      <Section title="ADR và tỉ lệ hủy">
        <p className="max-w-3xl text-[14.5px] text-oyster-ink">
          Góc trên bên trái là nhóm đáng đầu tư: giá phòng cao, ít hủy. Kích thước điểm theo doanh thu thực.
        </p>
        <DataState state={ranking} minHeight={340} isEmpty={(r) => r.items.length === 0}>
          {(r) => <Quadrant items={r.items} />}
        </DataState>
      </Section>
    </>
  )
}

function RankingTable({ data }: { data: RankingResponse }) {
  const maxShare = Math.max(...data.items.map((i) => i.revenue_share ?? 0))
  const market = data.dimension === 'market'
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-[14.5px]">
        <thead>
          <tr>
            <th className={`${th} text-right`}>#</th>
            <th className={th}>{market ? 'Quốc gia' : 'Kênh'}</th>
            {market && <th className={th}>Nhóm</th>}
            <th className={`${th} text-right`}>Booking</th>
            <th className={th}>Tỉ trọng doanh thu</th>
            <th className={`${th} text-right`}>ADR</th>
            <th className={th}>Tỉ lệ hủy</th>
            <th className={`${th} text-right`}>Doanh thu mất</th>
            <th className={`${th} text-right`}>Doanh thu thực</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((i) => (
            <tr key={i.key}>
              <td className={`${td} text-right font-mono text-oyster-ink tabular-nums`}>{i.rank}</td>
              <td className={td}>
                <span className="font-semibold">{i.label}</span>
                {market && <span className="ml-2 font-mono text-xs text-oyster-ink">{i.key}</span>}
              </td>
              {market && <td className={`${td} text-oyster-ink`}>{i.group}</td>}
              <td className={`${td} text-right font-mono tabular-nums`}>{num(i.bookings)}</td>
              <td className={td}>
                <BarCell value={i.revenue_share} max={maxShare} />
              </td>
              <td className={`${td} text-right font-mono tabular-nums`}>{eur(i.adr)}</td>
              <td className={td}>
                <BarCell value={i.cancellation_rate} tone="rust" />
              </td>
              <td className={`${td} text-right font-mono text-rust tabular-nums`}>{eurCompact(i.lost_revenue)}</td>
              <td className={`${td} text-right font-mono font-semibold tabular-nums`}>{eurCompact(i.realized_revenue)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-3 text-[13px] text-oyster-ink">
        {num(data.groups_ranked)} nhóm được xếp hạng
        {data.min_bookings > 0 && ` (bỏ nhóm dưới ${num(data.min_bookings)} booking vì ADR/tỉ lệ hủy dễ nhiễu)`} · tỉ
        trọng tính trên tổng doanh thu thực {eurCompact(data.total_realized_revenue)}.
      </p>
    </div>
  )
}

function Quadrant({ items }: { items: RankingItem[] }) {
  const points = items
    .filter((i) => i.adr != null && i.cancellation_rate != null)
    .map((i) => ({ ...i, x: i.cancellation_rate as number, y: i.adr as number, z: i.realized_revenue }))
  return (
    <div className="h-[340px] w-full min-w-0" role="img" aria-label="ADR theo tỉ lệ hủy">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 20, right: 40, bottom: 20, left: 4 }}>
          <CartesianGrid stroke={COLORS.kangaroo} />
          <XAxis
            type="number"
            dataKey="x"
            name="Tỉ lệ hủy"
            tickFormatter={(v) => pct(v, 0)}
            tickLine={false}
            axisLine={false}
            domain={[0, 'auto']}
            label={{ value: 'Tỉ lệ hủy →', position: 'insideBottomRight', offset: -12, fill: COLORS.oysterInk, fontFamily: FONT_MONO, fontSize: 11.5 }}
          />
          <YAxis
            type="number"
            dataKey="y"
            name="ADR"
            tickFormatter={(v) => `€${num(v)}`}
            tickLine={false}
            axisLine={false}
            width={56}
            domain={['auto', 'auto']}
          />
          <ZAxis type="number" dataKey="z" range={[60, 900]} />
          <Tooltip
            cursor={{ strokeDasharray: '2 3', stroke: COLORS.cedar }}
            isAnimationActive={false}
            content={({ active, payload }) => {
              const p = payload?.[0]?.payload as (RankingItem & { x: number }) | undefined
              if (!active || !p) return null
              return (
                <div className="min-w-[170px] bg-cedar px-3 py-2.5 text-[13px] leading-[1.45] text-merino">
                  <b className="font-semibold">{p.label}</b>
                  <TipRow label="Doanh thu thực" value={eurCompact(p.realized_revenue)} />
                  <TipRow label="ADR" value={eur(p.adr)} />
                  <TipRow label="Tỉ lệ hủy" value={pct(p.cancellation_rate)} />
                  <TipRow label="Booking" value={num(p.bookings)} />
                </div>
              )
            }}
          />
          <Scatter data={points} fill={COLORS.rifle} fillOpacity={0.75} stroke={COLORS.merino}>
            <LabelList dataKey="key" position="right" offset={10} fill={COLORS.cedar} fontFamily={FONT_UI} fontSize={12.5} fontWeight={600} />
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}
