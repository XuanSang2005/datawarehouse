// Number formatting in en-GB style (comma for thousands, dot for decimals). Money: EUR.
// Display formatting only; do NOT compute KPIs here (rates/ADR are computed from totals by the backend).

const nf0 = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 })
const nf1 = new Intl.NumberFormat('en-GB', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

export const MISSING = '—'

export function num(v: number | null | undefined): string {
  return v == null ? MISSING : nf0.format(v)
}

export function num1(v: number | null | undefined): string {
  return v == null ? MISSING : nf1.format(v)
}

/** 26,900,000 → "26.9M"; 262,000 → "262K"; 950 → "950" */
export function compact(v: number | null | undefined): string {
  if (v == null) return MISSING
  const a = Math.abs(v)
  if (a >= 1e6) return `${nf1.format(v / 1e6)}M`
  if (a >= 1e4) return `${nf0.format(v / 1e3)}K`
  return nf0.format(v)
}

export function eur(v: number | null | undefined): string {
  return v == null ? MISSING : `€${nf0.format(v)}`
}

export function eurCompact(v: number | null | undefined): string {
  return v == null ? MISSING : `€${compact(v)}`
}

/** Ratio 0–1 → "37.1%" */
export function pct(v: number | null | undefined, digits = 1): string {
  if (v == null) return MISSING
  return `${new Intl.NumberFormat('en-GB', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(v * 100)}%`
}

const WEEKDAY = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTH = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function parseIsoDate(iso: string): Date {
  return new Date(`${iso.slice(0, 10)}T00:00:00Z`)
}

/** "2017-08-22" → "Tue 22 Aug" */
export function dayLabel(iso: string): string {
  const d = parseIsoDate(iso)
  return `${WEEKDAY[d.getUTCDay()]} ${d.getUTCDate()} ${MONTH[d.getUTCMonth()]}`
}

/** "2017-08-22" → "22 Aug 2017" */
export function dateLabel(iso: string): string {
  const d = parseIsoDate(iso)
  return `${d.getUTCDate()} ${MONTH[d.getUTCMonth()]} ${d.getUTCFullYear()}`
}

/** "2017-08-22" → "22 Aug" */
export function dayMonth(iso: string): string {
  const d = parseIsoDate(iso)
  return `${d.getUTCDate()} ${MONTH[d.getUTCMonth()]}`
}

/** Add n days to an ISO date and return ISO (YYYY-MM-DD). */
export function addDays(iso: string, n: number): string {
  const d = parseIsoDate(iso)
  d.setUTCDate(d.getUTCDate() + n)
  return d.toISOString().slice(0, 10)
}

/** ISO week number of a date. */
export function isoWeek(iso: string): number {
  const d = parseIsoDate(iso)
  d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7) + 3) // Thursday of the same week
  const yearStart = Date.UTC(d.getUTCFullYear(), 0, 1)
  return Math.ceil(((d.getTime() - yearStart) / 86400000 + 1) / 7)
}
