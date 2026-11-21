// The app's ONE list of pages: both the nav bar and the Router read from here.
// To add a page: create a file in pages/ and add one line to this array.
import { lazy, type ReactElement } from 'react'

// Load each page on demand (code splitting): the first page opens faster and Recharts is not bundled into one big file.
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
  /** Show the hotel picker (Both / City / Resort) in the top bar */
  hotelFilter: boolean
}

export const routes: AppRoute[] = [
  { path: '/', label: 'Overview', element: <OverviewPage />, hotelFilter: true },
  { path: '/cancellation', label: 'Cancellations', element: <CancellationPage />, hotelFilter: true },
  { path: '/forecast', label: 'Forecast', element: <ForecastPage />, hotelFilter: true },
  { path: '/what-if', label: 'What-if', element: <WhatIfPage />, hotelFilter: true },
  { path: '/channels', label: 'Channels & markets', element: <ChannelMarketPage />, hotelFilter: true },
  { path: '/system', label: 'Pipeline', element: <SystemStatusPage />, hotelFilter: false },
]
