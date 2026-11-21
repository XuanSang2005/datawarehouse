// Mỗi endpoint backend = 1 hàm ở đây. Component KHÔNG gọi fetch trực tiếp.
import { apiGet } from './client'
import type { HealthResponse, PipelineRun } from '../types/api'

export const getHealth = () => apiGet<HealthResponse>('/api/health')

export const getPipelineRuns = (limit = 50) =>
  apiGet<PipelineRun[]>(`/api/pipeline/runs?limit=${limit}`)
