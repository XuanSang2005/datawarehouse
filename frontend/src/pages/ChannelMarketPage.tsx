// Channels and markets (G5) — user: Sales & Marketing Manager.
// Decisions supported: put marketing budget / channel contracts into the channels and countries that bring high
// realized revenue (after cancellations), good ADR and low cancellation rates. Data: GET /api/channels/ranking, /api/markets/ranking.
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
  { value: 'realized_revenue', label: 'Realized revenue' },
  { value: 'adr', label: 'ADR' },
  { value: 'cancellation_rate', label: 'Fewest cancellations' },
  { value: 'bookings', label: 'Bookings' },
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
  // The focal block always shows the channel/market with the most realized revenue, whatever the sort order
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
          title="Where does realized revenue come from?"
          aside={
            <Segmented<Dimension>
              label="Rank by"
              value={dim}
              onChange={setDim}
              options={[
                { value: 'channel', label: 'Channels' },
                { value: 'market', label: 'Markets' },
              ]}
            />
          }
        />
        <Focal className="flex flex-col justify-between gap-[18px] px-[22px] py-[22px] sm:px-7 sm:py-6">
          <Cap className="text-kangaroo">{dim === 'channel' ? 'Top-earning channel' : 'Largest market'}</Cap>
          <div>
            <BigNumber className="text-[clamp(64px,7vw,108px)]">{top ? pct(top.revenue_share, 0) : '—'}</BigNumber>
            <p className="mt-3.5 text-[17px] text-kangaroo">
              {top ? (
                <>
                  of realized revenue from <b className="font-semibold text-merino">{top.label}</b> · ADR {eur(top.adr)} · cancelled{' '}
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
        title={dim === 'channel' ? 'Channel ranking' : 'Market ranking'}
        aside={
          <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
            <Tabs label="Sort by" options={SORTS} value={sortBy} onChange={setSortBy} />
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

      <Section title="ADR vs cancellation rate">
        <p className="max-w-3xl text-[14.5px] text-oyster-ink">
          The top-left corner is where to invest: high room rates, few cancellations. Dot size shows realized revenue.
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
            <th className={th}>{market ? 'Country' : 'Channel'}</th>
            {market && <th className={th}>Group</th>}
            <th className={`${th} text-right`}>Bookings</th>
            <th className={th}>Revenue share</th>
            <th className={`${th} text-right`}>ADR</th>
            <th className={th}>Cancellation rate</th>
            <th className={`${th} text-right`}>Lost revenue</th>
            <th className={`${th} text-right`}>Realized revenue</th>
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
        {num(data.groups_ranked)} groups ranked
        {data.min_bookings > 0 && ` (groups under ${num(data.min_bookings)} bookings left out, as their ADR/cancellation rate is noisy)`} ·
        share of total realized revenue {eurCompact(data.total_realized_revenue)}.
      </p>
    </div>
  )
}

function Quadrant({ items }: { items: RankingItem[] }) {
  const points = items
    .filter((i) => i.adr != null && i.cancellation_rate != null)
    .map((i) => ({ ...i, x: i.cancellation_rate as number, y: i.adr as number, z: i.realized_revenue }))
  return (
    <div className="h-[340px] w-full min-w-0" role="img" aria-label="ADR by cancellation rate">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 20, right: 40, bottom: 20, left: 4 }}>
          <CartesianGrid stroke={COLORS.kangaroo} />
          <XAxis
            type="number"
            dataKey="x"
            name="Cancellation rate"
            tickFormatter={(v) => pct(v, 0)}
            tickLine={false}
            axisLine={false}
            domain={[0, 'auto']}
            label={{ value: 'Cancellation rate →', position: 'insideBottomRight', offset: -12, fill: COLORS.oysterInk, fontFamily: FONT_MONO, fontSize: 11.5 }}
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
                  <TipRow label="Realized revenue" value={eurCompact(p.realized_revenue)} />
                  <TipRow label="ADR" value={eur(p.adr)} />
                  <TipRow label="Cancellation rate" value={pct(p.cancellation_rate)} />
                  <TipRow label="Bookings" value={num(p.bookings)} />
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
