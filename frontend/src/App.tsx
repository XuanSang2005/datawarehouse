import { Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout'
import { Cap, PageHead } from './components/common/ledger'
import { routes } from './routes'

export default function App() {
  return (
    <AppLayout>
      <Suspense fallback={<Cap>Đang tải trang…</Cap>}>
      <Routes>
        {routes.map((r) => (
          <Route key={r.path} path={r.path} element={r.element} />
        ))}
        <Route path="*" element={<PageHead title="Không tìm thấy trang." />} />
      </Routes>
      </Suspense>
    </AppLayout>
  )
}
