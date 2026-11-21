// Trang kỹ thuật: kiểm tra FE ↔ BE ↔ DB có thông không và pipeline chạy ra sao.
// Khi có lỗi, mở trang này TRƯỚC TIÊN (xem docs/TROUBLESHOOTING.md).
import { getHealth, getPipelineRuns } from '../api/endpoints'
import ErrorBox from '../components/common/ErrorBox'
import StatusBadge from '../components/common/StatusBadge'
import { useApi } from '../hooks/useApi'

export default function SystemStatusPage() {
  const health = useApi(getHealth)
  const runs = useApi(() => getPipelineRuns(30))

  return (
    <section>
      <h1>Trạng thái hệ thống</h1>

      <div className="card">
        <h3>Kết nối</h3>
        {health.loading && <p className="muted">Đang kiểm tra…</p>}
        {health.error && <ErrorBox error={health.error} onRetry={health.reload} />}
        {health.data && (
          <p>
            Frontend → Backend <StatusBadge value="ok" /> · Backend → Database{' '}
            <StatusBadge value={health.data.database} /> · API v{health.data.version}
          </p>
        )}
      </div>

      <div className="card">
        <h3>Các bước ETL gần nhất</h3>
        {runs.error && <ErrorBox error={runs.error} onRetry={runs.reload} />}
        {runs.data && runs.data.length === 0 && (
          <p className="muted">Chưa có log. Chạy: python -m etl.run_pipeline</p>
        )}
        {runs.data && runs.data.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Bước</th>
                <th>Trạng thái</th>
                <th>Số dòng</th>
                <th>Ghi chú</th>
                <th>Bắt đầu</th>
              </tr>
            </thead>
            <tbody>
              {runs.data.map((r) => (
                <tr key={r.log_id}>
                  <td><code>{r.step}</code></td>
                  <td><StatusBadge value={r.status} /></td>
                  <td>{r.rows_affected?.toLocaleString() ?? '–'}</td>
                  <td>{r.message ?? ''}</td>
                  <td>{new Date(r.started_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  )
}
