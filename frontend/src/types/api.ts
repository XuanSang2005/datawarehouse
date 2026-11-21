// Kiểu dữ liệu trả về từ backend. PHẢI khớp với backend/app/schemas/*.py
// Sửa schema bên backend -> sửa luôn ở đây.

export interface HealthResponse {
  status: 'ok' | 'degraded'
  database: 'up' | 'down'
  version: string
}

export interface PipelineRun {
  log_id: number
  run_id: string
  step: string
  status: 'running' | 'success' | 'warning' | 'failed'
  rows_affected: number | null
  message: string | null
  started_at: string
  finished_at: string | null
}
