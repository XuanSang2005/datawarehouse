// Cột dọc đơn giản như "Cancellation by lead time" của prototype: số lớn trên đầu cột, nhãn mono dưới chân.
// Dùng div thay cho Recharts vì chỉ có ≤ 10 cột và cần chữ Bodoni trên đầu cột.
import { pct } from '../../lib/format'

export interface Column {
  key: string
  label: string
  value: number | null
  title?: string
}

export default function ColumnBars({
  columns,
  max,
  tone = 'rust',
  height = 190,
}: {
  columns: Column[]
  max?: number
  tone?: 'rust' | 'rifle'
  height?: number
}) {
  const top = max ?? Math.max(0.0001, ...columns.map((c) => c.value ?? 0))
  return (
    <div
      className="grid items-end gap-2 sm:gap-3.5"
      style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(0, 1fr))`, height }}
    >
      {columns.map((c) => (
        <div
          key={c.key}
          className="flex h-full min-w-0 flex-col items-center justify-end gap-2"
          title={c.title}
          aria-label={`${c.label}: ${pct(c.value)}`}
        >
          <b className="font-display text-lg font-medium sm:text-[22px]">{pct(c.value, 0)}</b>
          <i
            className={`block w-full max-w-16 origin-bottom transition-[height] duration-700 ease-ledger ${
              tone === 'rust' ? 'bg-rust' : 'bg-rifle'
            }`}
            style={{ height: `${((c.value ?? 0) / top) * (height - 60)}px` }}
          />
          <span className="max-w-full truncate font-mono text-[11px] text-oyster-ink sm:text-[11.5px]">
            {c.label}
          </span>
        </div>
      ))}
    </div>
  )
}
