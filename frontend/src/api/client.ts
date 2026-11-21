// Hàm gọi HTTP dùng chung. Mọi lỗi mạng/HTTP đều được chuẩn hóa thành ApiError.

export class ApiError extends Error {
  readonly status: number
  readonly path: string
  /** Gợi ý cách khắc phục từ backend (vd lệnh chạy script ML khi bảng gold.ml_* chưa có) */
  readonly hint: string | null

  constructor(status: number, path: string, message: string, hint: string | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.path = path
    this.hint = hint
  }
}

type QueryValue = string | number | boolean | null | undefined

/** Dựng query string, bỏ qua giá trị null/undefined/chuỗi rỗng. */
export function withQuery(path: string, params: Record<string, QueryValue> = {}): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== '') search.set(key, String(value))
  }
  const qs = search.toString()
  return qs ? `${path}?${qs}` : path
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let resp: Response
  try {
    resp = await fetch(path, { ...init, headers: { Accept: 'application/json', ...init.headers } })
  } catch {
    throw new ApiError(0, path, 'Không gọi được backend. Backend đã chạy chưa? (cổng 8000)')
  }

  if (!resp.ok) {
    let detail = resp.statusText
    let hint: string | null = null
    try {
      const body = await resp.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      hint = typeof body.hint === 'string' ? body.hint : null
    } catch {
      /* body không phải JSON */
    }
    throw new ApiError(resp.status, path, `${resp.status} ${detail}`, hint)
  }
  return (await resp.json()) as T
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path)
}

export function apiPost<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}
