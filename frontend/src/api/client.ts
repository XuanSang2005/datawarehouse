// Hàm gọi HTTP dùng chung. Mọi lỗi mạng/HTTP đều được chuẩn hóa thành ApiError.

export class ApiError extends Error {
  readonly status: number
  readonly path: string

  constructor(status: number, path: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.path = path
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  let resp: Response
  try {
    resp = await fetch(path, { headers: { Accept: 'application/json' } })
  } catch {
    throw new ApiError(0, path, 'Không gọi được backend. Backend đã chạy chưa? (cổng 8000)')
  }

  if (!resp.ok) {
    let detail = resp.statusText
    try {
      const body = await resp.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* body không phải JSON */
    }
    throw new ApiError(resp.status, path, `${resp.status} ${detail}`)
  }
  return (await resp.json()) as T
}
