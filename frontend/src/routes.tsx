// Danh sách trang DUY NHẤT của app: Sidebar và Router đều đọc từ đây.
// Thêm trang mới: tạo file trong pages/ rồi thêm 1 dòng vào mảng này.
import type { ReactElement } from 'react'
import OverviewPage from './pages/OverviewPage'
import CancellationPage from './pages/CancellationPage'
import ForecastPage from './pages/ForecastPage'
import WhatIfPage from './pages/WhatIfPage'
import SystemStatusPage from './pages/SystemStatusPage'

export interface AppRoute {
  path: string
  label: string
  element: ReactElement
}

export const routes: AppRoute[] = [
  { path: '/', label: 'Tổng quan KPI', element: <OverviewPage /> },
  { path: '/cancellation', label: 'Rủi ro hủy phòng', element: <CancellationPage /> },
  { path: '/forecast', label: 'Dự báo nhu cầu', element: <ForecastPage /> },
  { path: '/what-if', label: 'Mô phỏng What-if', element: <WhatIfPage /> },
  { path: '/system', label: 'Trạng thái hệ thống', element: <SystemStatusPage /> },
]
