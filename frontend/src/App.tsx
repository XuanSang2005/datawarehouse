import { Route, Routes } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout'
import { routes } from './routes'

export default function App() {
  return (
    <AppLayout>
      <Routes>
        {routes.map((r) => (
          <Route key={r.path} path={r.path} element={r.element} />
        ))}
        <Route path="*" element={<p>Không tìm thấy trang.</p>} />
      </Routes>
    </AppLayout>
  )
}
