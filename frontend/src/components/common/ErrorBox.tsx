import { ApiError } from '../../api/client'

/** Consistent error box. Also shows the fix-it hint returned by the backend, e.g. the command to run the ML script. */
export default function ErrorBox({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  const hint = error instanceof ApiError ? error.hint : null
  return (
    <div role="alert" className="flex flex-col gap-2 border-l-2 border-rust bg-kangaroo/40 px-4 py-3 text-sm">
      <p>
        <strong className="font-semibold text-rust">Error:</strong> {error.message}
      </p>
      {hint && (
        <p className="font-mono text-[13px] text-cedar">
          <span className="text-oyster-ink">How to fix: </span>
          {hint}
        </p>
      )}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="self-start cursor-pointer border border-rifle px-3 py-1.5 text-[13px] font-semibold text-rifle hover:bg-kangaroo"
        >
          Try again
        </button>
      )}
    </div>
  )
}
