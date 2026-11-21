import type { ReactNode } from 'react'
import ErrorBox from './ErrorBox'

interface Props<T> {
  state: { data: T | null; error: Error | null; loading: boolean; reload: () => void }
  /** Trả true nếu dữ liệu rỗng (hiện thông báo thay vì nội dung) */
  isEmpty?: (data: T) => boolean
  empty?: ReactNode
  /** Chiều cao giữ chỗ khi đang tải lần đầu, để bố cục không nhảy */
  minHeight?: number
  children: (data: T) => ReactNode
}

/** Trạng thái loading / lỗi / rỗng thống nhất cho mọi khối dữ liệu. */
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
        Đang tải…
      </div>
    )
  }
  if (isEmpty?.(data)) {
    return (
      <p className="border-t border-kangaroo py-6 text-oyster-ink">
        {empty ?? 'Không có dữ liệu cho bộ lọc này.'}
      </p>
    )
  }
  return <div className={`transition-opacity ${loading ? 'opacity-60' : ''}`}>{children(data)}</div>
}
