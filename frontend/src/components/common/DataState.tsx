import type { ReactNode } from 'react'
import ErrorBox from './ErrorBox'

interface Props<T> {
  state: { data: T | null; error: Error | null; loading: boolean; reload: () => void }
  /** Return true if the data is empty (shows a message instead of the content) */
  isEmpty?: (data: T) => boolean
  empty?: ReactNode
  /** Placeholder height during the first load, so the layout does not jump */
  minHeight?: number
  children: (data: T) => ReactNode
}

/** Consistent loading / error / empty states for every data block. */
export default function DataState<T>({ state, isEmpty, empty, minHeight = 120, children }: Props<T>) {
  const { data, error, loading, reload } = state
  if (error) return <ErrorBox error={error} onRetry={reload} />
  if (data == null) {
    return (
      <div
        className="flex items-center justify-center bg-kangaroo/25 font-mono text-xs tracking-[0.14em] text-oyster-ink uppercase"
        style={{ minHeight }}
        aria-busy="true"
      >
        Loading…
      </div>
    )
  }
  if (isEmpty?.(data)) {
    return (
      <p className="border-t border-kangaroo py-6 text-oyster-ink">
        {empty ?? 'No data for these filters.'}
      </p>
    )
  }
  return <div className={`transition-opacity ${loading ? 'opacity-60' : ''}`}>{children(data)}</div>
}
