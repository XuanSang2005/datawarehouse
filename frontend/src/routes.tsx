// Danh sách trang DUY NHẤT của app: thanh điều hướng và Router đều đọc từ đây.
// Thêm trang mới: tạo file trong pages/ rồi thêm 1 dòng vào mảng này.
import { lazy, type ReactElement } from 'react'

// Tải từng trang khi cần (code splitting): trang đầu mở nhanh hơn, Recharts không nằm chung 1 file lớn.
const OverviewPage = lazy(() => import('./pages/OverviewPage'))
const CancellationPage = lazy(() => import('./pages/CancellationPage'))
const ForecastPage = lazy(() => import('./pages/ForecastPage'))
const WhatIfPage = lazy(() => import('./pages/WhatIfPage'))
const ChannelMarketPage = lazy(() => import('./pages/ChannelMarketPage'))
const SystemStatusPage = lazy(() => import('./pages/SystemStatusPage'))

export interface AppRoute {
  path: string
  label: string
  element: ReactElement
  /** Hiện bộ chọn khách sạn (Cả hai / City / Resort) ở thanh trên */
  hotelFilter: boolean
}

export const routes: AppRoute[] = [
  { path: '/', label: 'Tổng quan', element: <OverviewPage />, hotelFilter: true },
  { path: '/cancellation', label: 'Rủi ro hủy', element: <CancellationPage />, hotelFilter: true },
  { path: '/forecast', label: 'Dự báo', element: <ForecastPage />, hotelFilter: true },
  { path: '/what-if', label: 'What-if', element: <WhatIfPage />, hotelFilter: true },
  { path: '/channels', label: 'Kênh & thị trường', element: <ChannelMarketPage />, hotelFilter: true },
  { path: '/system', label: 'Pipeline', element: <SystemStatusPage />, hotelFilter: false },
]
