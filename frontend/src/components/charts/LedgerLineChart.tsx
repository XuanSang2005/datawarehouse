// Biểu đồ đường theo phong cách prototype, dựng trên Recharts:
// chỉ kẻ lưới ngang, chữ trục mono, nhãn tên đặt ngay cuối đường (không cần legend rời), crosshair nét đứt,
// tooltip nền Cedar. Hỗ trợ dải khoảng tin cậy, vùng đánh dấu, đường 0 và click để drill-down.
import type { ReactNode } from 'react'
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { COLORS, FONT_MONO, FONT_UI } from '../../lib/theme'

export type ChartRow = Record<string, string | number | null | [number, number] | boolean | undefined>

export interface LineSeries {
  key: string
  name: string
  color: string
  dashed?: boolean
  width?: number
  /** Hiện tên ở cuối đường */
  endLabel?: boolean
  /** Dịch nhãn cuối theo trục y (tránh chồng nhau) */
  labelDy?: number
}

export interface BandSeries {
  /** Khóa chứa mảng [cận dưới, cận trên] */
  key: string
  color: string
  opacity?: number
}

interface Props {
  data: ChartRow[]
  xKey: string
  series: LineSeries[]
  bands?: BandSeries[]
  height?: number
  yFormat: (v: number) => string
  xFormat?: (v: string) => string
  yDomain?: [number | 'auto' | 'dataMin', number | 'auto' | 'dataMax']
  /** Nội dung tooltip cho 1 dòng dữ liệu */
  tooltip: (row: ChartRow) => ReactNode
  /** Click 1 điểm (drill-down) */
  onPointClick?: (row: ChartRow) => void
  /** Vùng nền đánh dấu, vd giai đoạn dự báo */
  highlight?: { from: string; to: string; label: string }
  zeroLine?: boolean
  /** Phần tử Recharts thêm vào (ReferenceDot...) */
  children?: ReactNode
  label: string
}

function lastIndexWithValue(data: ChartRow[], key: string): number {
  for (let i = data.length - 1; i >= 0; i--) if (data[i][key] != null) return i
  return -1
}

export default function LedgerLineChart({
  data,
  xKey,
  series,
  bands = [],
  height = 300,
  yFormat,
  xFormat,
  yDomain = ['auto', 'auto'],
  tooltip,
  onPointClick,
  highlight,
  zeroLine,
  children,
  label,
}: Props) {
  const hasEndLabels = series.some((s) => s.endLabel)
  return (
    <div role="img" aria-label={label} className="w-full min-w-0" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart
          data={data}
          margin={{ top: 36, right: hasEndLabels ? 74 : 12, bottom: 4, left: 4 }}
          onClick={(state) => {
            const i = Number(state?.activeTooltipIndex)
            if (onPointClick && Number.isInteger(i) && data[i]) onPointClick(data[i])
          }}
          style={{ cursor: onPointClick ? 'pointer' : undefined }}
        >
          <CartesianGrid vertical={false} stroke={COLORS.kangaroo} />
          {highlight && (
            <ReferenceArea
              x1={highlight.from}
              x2={highlight.to}
              fill={COLORS.kangaroo}
              fillOpacity={0.45}
              label={{
                value: highlight.label,
                position: 'insideTopLeft',
                fill: COLORS.oysterInk,
                fontFamily: FONT_MONO,
                fontSize: 11.5,
              }}
            />
          )}
          <XAxis
            dataKey={xKey}
            tickFormatter={xFormat}
            tickLine={false}
            axisLine={false}
            minTickGap={24}
            tickMargin={8}
          />
          <YAxis
            tickFormatter={yFormat}
            tickLine={false}
            axisLine={false}
            width={56}
            domain={yDomain}
            tickCount={5}
          />
          {zeroLine && <ReferenceLine y={0} stroke={COLORS.cedar} />}
          {bands.map((b) => (
            <Area
              key={b.key}
              dataKey={b.key}
              stroke="none"
              fill={b.color}
              fillOpacity={b.opacity ?? 0.16}
              isAnimationActive={false}
              activeDot={false}
              connectNulls={false}
            />
          ))}
          {series.map((s) => {
            const last = lastIndexWithValue(data, s.key)
            return (
              <Line
                key={s.key}
                dataKey={s.key}
                name={s.name}
                stroke={s.color}
                strokeWidth={s.width ?? 2.5}
                strokeDasharray={s.dashed ? '6 6' : undefined}
                strokeLinecap="round"
                strokeLinejoin="round"
                dot={false}
                activeDot={{ r: 5, fill: s.color, stroke: COLORS.merino, strokeWidth: 2 }}
                connectNulls={false}
                animationDuration={1200}
                label={
                  s.endLabel
                    ? (p: { x?: number | string; y?: number | string; index?: number }) =>
                        p.index === last ? (
                          <g key={`${s.key}-end`}>
                            <rect x={Number(p.x) - 4} y={Number(p.y) - 4} width={8} height={8} fill={s.color} />
                            <text
                              x={Number(p.x) + 12}
                              y={Number(p.y) + 5 + (s.labelDy ?? 0)}
                              fontFamily={FONT_UI}
                              fontSize={13.5}
                              fontWeight={600}
                              fill={COLORS.cedar}
                            >
                              {s.name}
                            </text>
                          </g>
                        ) : (
                          <g key={`${s.key}-${p.index}`} />
                        )
                    : undefined
                }
              />
            )
          })}
          {children}
          <Tooltip
            cursor={{ stroke: COLORS.cedar, strokeWidth: 1, strokeDasharray: '2 3' }}
            isAnimationActive={false}
            content={({ active, payload }) => {
              const row = payload?.[0]?.payload as ChartRow | undefined
              if (!active || !row) return null
              return (
                <div className="min-w-[150px] bg-cedar px-3 py-2.5 text-[13px] leading-[1.45] text-merino">
                  {tooltip(row)}
                </div>
              )
            }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Một dòng trong tooltip: nhãn trái, số phải. */
export function TipRow({ label, value, color }: { label: ReactNode; value: ReactNode; color?: string }) {
  return (
    <div className="flex justify-between gap-3.5">
      <span className="inline-flex items-center gap-1.5">
        {color && <i className="inline-block size-2" style={{ background: color }} />}
        {label}
      </span>
      <b className="font-mono font-medium tabular-nums">{value}</b>
    </div>
  )
}
