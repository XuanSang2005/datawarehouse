// Status as a coloured square + text, like the "Data quality" section of the prototype.
const TONE: Record<string, string> = {
  ok: 'bg-rifle',
  up: 'bg-rifle',
  success: 'bg-rifle',
  warning: 'bg-brass',
  degraded: 'bg-brass',
  running: 'bg-brass',
  failed: 'bg-rust',
  down: 'bg-rust',
}

export default function StatusBadge({ value, label }: { value: string; label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm">
      <i className={`inline-block size-[9px] flex-none ${TONE[value] ?? 'bg-oyster'}`} />
      {label ?? value}
    </span>
  )
}
