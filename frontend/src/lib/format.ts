// Định dạng số theo kiểu Việt Nam (dấu chấm ngăn nghìn, dấu phẩy thập phân). Tiền: EUR.
// Chỉ định dạng để hiển thị; KHÔNG tính KPI ở đây (tỉ lệ/ADR đã được backend tính từ tổng).

const nf0 = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 })
const nf1 = new Intl.NumberFormat('vi-VN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

export const MISSING = '—'

export function num(v: number | null | undefined): string {
  return v == null ? MISSING : nf0.format(v)
}

export function num1(v: number | null | undefined): string {
  return v == null ? MISSING : nf1.format(v)
}

/** 26.900.000 → "26,9M"; 262.000 → "262K"; 950 → "950" */
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

/** Tỉ lệ 0–1 → "37,1%" */
export function pct(v: number | null | undefined, digits = 1): string {
  if (v == null) return MISSING
  return `${new Intl.NumberFormat('vi-VN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(v * 100)}%`
}

const WEEKDAY = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7']

function parseIsoDate(iso: string): Date {
  return new Date(`${iso.slice(0, 10)}T00:00:00Z`)
}

/** "2017-08-22" → "T3 22/8" */
export function dayLabel(iso: string): string {
  const d = parseIsoDate(iso)
  return `${WEEKDAY[d.getUTCDay()]} ${d.getUTCDate()}/${d.getUTCMonth() + 1}`
}

/** "2017-08-22" → "22/8/2017" */
export function dateLabel(iso: string): string {
  const d = parseIsoDate(iso)
  return `${d.getUTCDate()}/${d.getUTCMonth() + 1}/${d.getUTCFullYear()}`
}

/** "2017-08-22" → "22/8" */
export function dayMonth(iso: string): string {
  const d = parseIsoDate(iso)
  return `${d.getUTCDate()}/${d.getUTCMonth() + 1}`
}

/** Cộng n ngày vào ngày ISO, trả về ISO (YYYY-MM-DD). */
export function addDays(iso: string, n: number): string {
  const d = parseIsoDate(iso)
  d.setUTCDate(d.getUTCDate() + n)
  return d.toISOString().slice(0, 10)
}

/** Số tuần ISO của một ngày. */
export function isoWeek(iso: string): number {
  const d = parseIsoDate(iso)
  d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7) + 3) // Thứ Năm cùng tuần
  const yearStart = Date.UTC(d.getUTCFullYear(), 0, 1)
  return Math.ceil(((d.getTime() - yearStart) / 86400000 + 1) / 7)
}
