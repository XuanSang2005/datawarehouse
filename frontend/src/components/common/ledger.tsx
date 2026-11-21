// Small UI blocks in the prototype's "ledger" style (docs/design/prototype/).
// All styling is Tailwind utility classes; colour/font tokens are declared in styles/global.css (@theme).
import type { CSSProperties, ReactNode } from 'react'
import { compact, eur, eurCompact, pct } from '../../lib/format'

/** Uppercase, letter-spaced mono caption (".cap" in the prototype). */
export function Cap({ children, className = '' }: { children: ReactNode; className?: string }) {
  // Default colour only when the caller sets none: two text-* colour classes would conflict
  // (e.g. text-kangaroo on the dark focal block lost to text-oyster-ink and became unreadable).
  const hasColour = /(^|\s)text-(merino|kangaroo|oyster|oyster-ink|rifle|cedar|rust|brass)(\s|$)/.test(className)
  return (
    <span
      className={`font-mono text-[11.5px] tracking-[0.14em] uppercase ${hasColour ? '' : 'text-oyster-ink'} ${className}`}
    >
      {children}
    </span>
  )
}

/** Large page title (Archivo). */
export function PageHead({ title, aside }: { title: ReactNode; aside?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4 animate-rise">
      <h1 className="font-display text-[clamp(40px,5.6vw,76px)] leading-[0.98] tracking-[-0.02em]">
        {title}
      </h1>
      {aside}
    </div>
  )
}

/** A content section: top rule, Archivo title, right-hand aside (legend/tabs). */
export function Section({
  title,
  aside,
  children,
  className = '',
}: {
  title: ReactNode
  aside?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`flex min-w-0 flex-col gap-5 animate-rise ${className}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-3 border-t border-cedar pt-3.5">
        <h2 className="font-display text-[26px] leading-[1.1] tracking-[-0.01em] sm:text-[30px]">{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  )
}

/** Rifle-green block: the single focal point of each page. */
export function Focal({
  children,
  className = '',
  style,
}: {
  children: ReactNode
  className?: string
  style?: CSSProperties
}) {
  return (
    <div className={`relative overflow-hidden bg-rifle text-merino animate-rise ${className}`} style={style}>
      {children}
    </div>
  )
}

/** Very large number on the Focal block. */
export function BigNumber({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`font-display font-bold leading-[0.86] tracking-[-0.035em] whitespace-nowrap tabular-nums ${className}`}
    >
      {children}
    </div>
  )
}

/** Small raised currency sign, as in the prototype (".cur"). */
export function Cur({ children = '€' }: { children?: ReactNode }) {
  return (
    <span className="mr-[0.1em] align-[1.05em] font-sans text-[0.4em] font-medium tracking-normal">
      {children}
    </span>
  )
}

/** EUR amount: small € sign + value (shortened to K/M when compact). */
export function Money({
  value,
  compactForm = false,
  signed = false,
}: {
  value: number | null | undefined
  compactForm?: boolean
  signed?: boolean
}) {
  if (value == null) return <>—</>
  const text = (compactForm ? eurCompact(Math.abs(value)) : eur(Math.abs(value))).slice(1)
  const sign = signed ? (value < 0 ? '−' : '+') : value < 0 ? '−' : ''
  return (
    <>
      <Cur>{`${sign}€`}</Cur>
      {text}
    </>
  )
}

interface SegmentedOption<T extends string | number | null> {
  value: T
  label: ReactNode
}

/** Bordered toggle-button group (the hotel picker in the top bar). */
export function Segmented<T extends string | number | null>({
  options,
  value,
  onChange,
  label,
  tone = 'light',
}: {
  options: SegmentedOption<T>[]
  value: T
  onChange: (v: T) => void
  label: string
  tone?: 'light' | 'focal'
}) {
  const border = tone === 'focal' ? 'border-merino' : 'border-cedar'
  return (
    <div role="group" aria-label={label} className={`inline-flex border ${border}`}>
      {options.map((o, i) => {
        const on = o.value === value
        const look =
          tone === 'focal'
            ? on
              ? 'bg-merino text-rifle'
              : 'text-merino hover:bg-merino/15'
            : on
              ? 'bg-rifle text-merino'
              : 'text-cedar hover:bg-kangaroo'
        return (
          <button
            key={String(o.value)}
            type="button"
            aria-pressed={on}
            onClick={() => onChange(o.value)}
            className={`cursor-pointer px-3.5 py-[7px] text-[13.5px] font-semibold transition-colors ${
              i > 0 ? `border-l ${border}` : ''
            } ${look}`}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
}

/** Underlined tabs (switch the view within a Section). */
export function Tabs<T extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: SegmentedOption<T>[]
  value: T
  onChange: (v: T) => void
  label: string
}) {
  return (
    <div role="group" aria-label={label} className="inline-flex flex-wrap gap-x-[18px] gap-y-1">
      {options.map((o) => {
        const on = o.value === value
        return (
          <button
            key={o.value}
            type="button"
            aria-pressed={on}
            onClick={() => onChange(o.value)}
            className={`cursor-pointer border-b-2 py-0.5 text-sm font-semibold transition-colors ${
              on ? 'border-rifle text-cedar' : 'border-transparent text-oyster-ink hover:text-cedar'
            }`}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
}

/** Horizontal bar + number (share / cancellation-rate columns in tables). */
export function BarCell({
  value,
  max = 1,
  tone = 'rifle',
  text,
}: {
  value: number | null
  max?: number
  tone?: 'rifle' | 'rust'
  text?: string
}) {
  const width = value == null || max <= 0 ? 0 : Math.min(100, (value / max) * 100)
  return (
    <div className="flex min-w-[150px] items-center gap-3">
      <span className="h-1.5 flex-1 overflow-hidden bg-kangaroo">
        <i
          className={`block h-full transition-[width] duration-700 ease-ledger ${tone === 'rust' ? 'bg-rust' : 'bg-rifle'}`}
          style={{ width: `${width}%` }}
        />
      </span>
      <span className="w-14 text-right font-mono text-[13px] tabular-nums">{text ?? pct(value)}</span>
    </div>
  )
}

export interface KpiItem {
  label: string
  value: ReactNode
  alert?: boolean
  note?: ReactNode
}

/** KPI row separated by vertical rules (".kpis" in the prototype). */
export function KpiStrip({ items }: { items: KpiItem[] }) {
  return (
    <div className="grid grid-cols-2 gap-y-6 animate-rise md:grid-cols-4">
      {items.map((k, i) => (
        <div
          key={k.label}
          className={`flex min-w-0 flex-col gap-2.5 pr-3.5 sm:pr-6 ${
            i === 0 ? '' : 'border-l border-kangaroo pl-3.5 sm:pl-6'
          } ${i === 2 ? 'max-md:border-l-0 max-md:pl-0 max-md:sm:pl-0' : ''}`}
        >
          <Cap>{k.label}</Cap>
          <span
            className={`font-display font-bold text-[clamp(34px,4.4vw,62px)] leading-[0.95] tracking-[-0.02em] whitespace-nowrap tabular-nums ${
              k.alert ? 'text-rust' : ''
            }`}
          >
            {k.value}
          </span>
          {k.note && <span className="text-[13px] text-oyster-ink">{k.note}</span>}
        </div>
      ))}
    </div>
  )
}

/** Chart legend: colour swatch + label. */
export function Legend({ items }: { items: { label: string; color: string; dashed?: boolean; box?: boolean }[] }) {
  return (
    <div className="flex flex-wrap gap-[18px] text-[13.5px]">
      {items.map((it) => (
        <span key={it.label} className="inline-flex items-center gap-2">
          {it.dashed ? (
            <i className="inline-block h-0 w-[18px] border-t-2 border-dashed" style={{ borderColor: it.color }} />
          ) : it.box ? (
            <i className="inline-block h-2.5 w-[18px] opacity-30" style={{ background: it.color }} />
          ) : (
            <i className="inline-block h-[3px] w-[18px]" style={{ background: it.color }} />
          )}
          {it.label}
        </span>
      ))}
    </div>
  )
}

/** Ledger-style table: uppercase mono header, rows separated by thin rules. */
export const th = 'whitespace-nowrap pr-3.5 pb-2.5 text-left font-mono text-[11px] font-normal tracking-[0.12em] uppercase text-oyster-ink'
export const td = 'whitespace-nowrap border-t border-kangaroo py-3.5 pr-3.5 align-middle'

/** Compact value with a small € sign. */
export function MoneyCompact({ value }: { value: number | null | undefined }) {
  return <Money value={value} compactForm />
}

export function Count({ value }: { value: number | null | undefined }) {
  return <>{compact(value)}</>
}
