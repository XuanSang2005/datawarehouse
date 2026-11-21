import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'

/** Short notice at the bottom of the screen. Returns [element to render, function that shows a message]. */
export function useToast(): [ReactNode, (message: string) => void] {
  const [message, setMessage] = useState<string | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  const show = useCallback((msg: string) => {
    setMessage(msg)
    clearTimeout(timer.current)
    timer.current = setTimeout(() => setMessage(null), 2400)
  }, [])

  useEffect(() => () => clearTimeout(timer.current), [])

  const node = (
    <div
      role="status"
      className={`pointer-events-none fixed bottom-6 left-1/2 z-[60] -translate-x-1/2 bg-cedar px-[18px] py-3 text-sm font-medium text-merino transition-all duration-300 ${
        message ? 'translate-y-0 opacity-100' : 'translate-y-5 opacity-0'
      }`}
    >
      {message}
    </div>
  )
  return [node, show]
}
