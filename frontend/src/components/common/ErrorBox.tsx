import { ApiError } from '../../api/client'

/** Hộp lỗi thống nhất. Hiển thị cả gợi ý khắc phục (hint) mà backend trả về, vd lệnh chạy script ML. */
export default function ErrorBox({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  const hint = error instanceof ApiError ? error.hint : null
  return (
    <div role="alert" className="flex flex-col gap-2 border-l-2 border-rust bg-kangaroo/40 px-4 py-3 text-sm">
      <p>
        <strong className="font-semibold text-rust">Lỗi:</strong> {error.message}
      </p>
      {hint && (
        <p className="font-mono text-[13px] text-cedar">
          <span className="text-oyster-ink">Cách khắc phục: </span>
          {hint}
        </p>
      )}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="self-start cursor-pointer border border-rifle px-3 py-1.5 text-[13px] font-semibold text-rifle hover:bg-kangaroo"
        >
          Thử lại
        </button>
      )}
    </div>
  )
}
