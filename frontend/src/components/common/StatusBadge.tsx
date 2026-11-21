const TONE: Record<string, string> = {
  ok: 'good', up: 'good', success: 'good',
  warning: 'warn', degraded: 'warn', running: 'warn',
  failed: 'bad', down: 'bad',
}

export default function StatusBadge({ value }: { value: string }) {
  return <span className={`badge badge-${TONE[value] ?? 'neutral'}`}>{value}</span>
}
