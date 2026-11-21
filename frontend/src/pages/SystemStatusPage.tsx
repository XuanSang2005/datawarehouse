// Pipeline & system status: is FE ↔ BE ↔ DB connected, and how did the latest ETL run go.
// When something breaks, open this page FIRST (see docs/TROUBLESHOOTING.md).
// Figures come from meta.etl_run_log (GET /api/pipeline/runs) for the latest run.
import { getHealth, getPipelineRuns } from '../api/endpoints'
import DataState from '../components/common/DataState'
import { Cap, PageHead, Section, td, th } from '../components/common/ledger'
import StatusBadge from '../components/common/StatusBadge'
import { useApi } from '../hooks/useApi'
import { num } from '../lib/format'
import type { PipelineRun } from '../types/api'

const LAYER_NOTE: Record<string, string> = {
  extract: 'Sources',
  bronze: 'As is, text',
  silver: 'Typed, checked',
  gold: 'Star schema',
}

function fileName(step: string): string {
  return step.split('/').slice(1).join('/').replace(/^\d+_/, '').replace(/\.sql$/, '')
}

/** Group gold steps by table kind (as in the prototype: "fact_booking · fact_daily_occupancy — 2 facts"). */
function goldGroups(steps: PipelineRun[]): { names: string; label: string }[] {
  const names = steps.map((s) => fileName(s.step))
  const groups: [string, (n: string) => boolean, string][] = [
    ['fact', (n) => n.startsWith('fact_'), 'fact'],
    ['dim', (n) => n.startsWith('dim_'), 'dimension'],
    ['kpi', (n) => n.startsWith('kpi_'), 'KPI view'],
  ]
  const out = groups
    .map(([, test, label]) => {
      const g = names.filter(test)
      return { names: g.map((n) => n.replace(/^(fact|dim|kpi)_/, '')).join(' · '), label: `${g.length} ${label}${g.length === 1 ? '' : 's'}`, count: g.length }
    })
    .filter((g) => g.count > 0)
    .map(({ names: n, label }) => ({ names: n, label }))
  out.push({ names: 'ml_booking_risk · ml_demand_forecast', label: 'from ml/ (not built by the pipeline)' })
  return out
}

/** "21 Nov 2017, 08:14" */
const RUN_TIME: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }

function runDuration(steps: PipelineRun[]): string {
  const start = Math.min(...steps.map((s) => new Date(s.started_at).getTime()))
  const end = Math.max(...steps.map((s) => new Date(s.finished_at ?? s.started_at).getTime()))
  return `${Math.max(1, Math.round((end - start) / 1000))} s`
}

export default function SystemStatusPage() {
  const health = useApi(getHealth)
  const runs = useApi(() => getPipelineRuns(300))

  const latestId = runs.data?.[0]?.run_id
  const latest = (runs.data ?? []).filter((r) => r.run_id === latestId).reverse()
  const layer = (prefix: string) => latest.filter((r) => r.step.startsWith(`${prefix}/`))
  const checks = layer('checks')
  const loads = new Map(layer('bronze').filter((r) => r.step.includes('load_')).map((r) => [r.step.split('load_')[1], r]))
  const failed = latest.some((r) => r.status === 'failed')

  return (
    <>
      <PageHead
        title="From CSV to decisions"
        aside={
          latest.length > 0 && (
            <StatusBadge
              value={failed ? 'failed' : 'success'}
              label={`Last run ${new Date(latest[0].started_at).toLocaleString('en-GB', RUN_TIME)} · ${runDuration(latest)}`}
            />
          )
        }
      />

      <Section title="Connections">
        <DataState state={health} minHeight={60}>
          {(h) => (
            <div className="flex flex-wrap gap-x-10 gap-y-3">
              <StatusBadge value="ok" label="Frontend → Backend" />
              <StatusBadge value={h.database} label={`Backend → Database (${h.database})`} />
              <Cap>API v{h.version}</Cap>
            </div>
          )}
        </DataState>
      </Section>

      <DataState
        state={runs}
        minHeight={240}
        isEmpty={(r) => r.length === 0}
        empty={
          <>
            No logs yet. Run: <code className="font-mono">python -m etl.run_pipeline</code>
          </>
        }
      >
        {() => (
          <div className="grid animate-rise md:grid-cols-5">
            {(['extract', 'bronze', 'silver', 'gold'] as const).map((p, i) => {
              const steps = layer(p).filter((s) => p !== 'bronze' || !s.step.includes('load_'))
              const hl = p === 'gold'
              return (
                <div
                  key={p}
                  className={`relative flex min-w-0 flex-col gap-3.5 border-kangaroo max-md:border-t max-md:py-[18px] ${
                    hl
                      ? 'bg-rifle p-[22px] text-merino md:pl-[26px]'
                      : `md:pr-[22px] ${i === 0 ? 'max-md:border-t-0 max-md:pt-0' : 'md:border-l md:pl-[26px]'}`
                  }`}
                >
                  <Cap className={hl ? 'text-kangaroo' : ''}>{LAYER_NOTE[p]}</Cap>
                  <h3 className="font-display text-[34px] leading-none">{p === 'extract' ? 'Raw' : p[0].toUpperCase() + p.slice(1)}</h3>
                  <ul className="flex flex-col gap-3">
                    {p === 'gold' ? (
                      goldGroups(steps).map((g) => (
                        <li key={g.label} className="flex flex-col gap-px">
                          <code className="font-mono text-[13px] [overflow-wrap:anywhere]">{g.names}</code>
                          <span className="text-[13px] text-kangaroo">{g.label}</span>
                        </li>
                      ))
                    ) : steps.map((s) => {
                      const name = p === 'extract' ? s.step.split('/')[1] : fileName(s.step)
                      const rows = p === 'bronze' ? loads.get(fileName(s.step))?.rows_affected : s.rows_affected
                      return (
                        <li key={s.log_id} className="flex flex-col gap-px">
                          <code className="font-mono text-[13px] [overflow-wrap:anywhere]">{name}</code>
                          <span className={`text-[13px] ${hl ? 'text-kangaroo' : 'text-oyster-ink'}`}>
                            {s.status !== 'success' ? s.status : rows != null ? `${num(rows)} rows` : 'done'}
                          </span>
                        </li>
                      )
                    })}
                  </ul>
                </div>
              )
            })}
            <div className="flex min-w-0 flex-col gap-3.5 border-kangaroo max-md:border-t max-md:py-[18px] md:pl-[26px]">
              <Cap>Read only</Cap>
              <h3 className="font-display text-[34px] leading-none">App</h3>
              <ul className="flex flex-col gap-3">
                <li className="flex flex-col gap-px">
                  <code className="font-mono text-[13px]">FastAPI</code>
                  <span className="text-[13px] text-oyster-ink">gold & meta</span>
                </li>
                <li className="flex flex-col gap-px">
                  <code className="font-mono text-[13px]">ml/ → gold.ml_*</code>
                  <span className="text-[13px] text-oyster-ink">cancellation risk, forecast</span>
                </li>
                <li className="flex flex-col gap-px">
                  <code className="font-mono text-[13px]">Revenue Desk</code>
                  <span className="text-[13px] text-oyster-ink">this screen</span>
                </li>
              </ul>
            </div>
          </div>
        )}
      </DataState>

      {checks.length > 0 && (
        <Section title="Data quality">
          <div className="grid grid-cols-2 gap-y-6 md:grid-cols-4">
            {checks.map((c, i) => (
              <div
                key={c.log_id}
                className={`flex flex-col gap-1.5 pt-1 pr-6 ${i % 4 === 0 ? '' : 'md:border-l md:border-kangaroo md:pl-6'} ${
                  i % 2 === 1 ? 'max-md:border-l max-md:border-kangaroo max-md:pl-6' : ''
                }`}
              >
                <b className="font-display text-[48px] leading-none font-medium tabular-nums">{num(c.rows_affected ?? 0)}</b>
                <span className="font-semibold [overflow-wrap:anywhere]">{fileName(c.step).replace(/_/g, ' ')}</span>
                <StatusBadge
                  value={c.status}
                  label={c.status === 'success' ? 'Passed' : c.status === 'warning' ? 'Warning (handled in gold)' : 'Failed'}
                />
              </div>
            ))}
          </div>
        </Section>
      )}

      <Section title="Latest ETL steps">
        <DataState state={runs} isEmpty={(r) => r.length === 0}>
          {(r) => (
            <details className="group">
              <summary className="cursor-pointer list-none font-semibold text-rifle underline underline-offset-4">
                <span className="group-open:hidden">Show the latest {num(Math.min(r.length, 40))} steps</span>
                <span className="hidden group-open:inline">Hide details</span>
              </summary>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full border-collapse text-[14.5px]">
                <thead>
                  <tr>
                    <th className={th}>Step</th>
                    <th className={th}>Status</th>
                    <th className={`${th} text-right`}>Rows</th>
                    <th className={th}>Message</th>
                    <th className={th}>Started</th>
                  </tr>
                </thead>
                <tbody>
                  {r.slice(0, 40).map((s) => (
                    <tr key={s.log_id}>
                      <td className={td}>
                        <code className="font-mono text-[13px]">{s.step}</code>
                      </td>
                      <td className={td}>
                        <StatusBadge value={s.status} />
                      </td>
                      <td className={`${td} text-right font-mono tabular-nums`}>{s.rows_affected != null ? num(s.rows_affected) : '–'}</td>
                      <td className={`${td} text-oyster-ink`}>{s.message ?? ''}</td>
                      <td className={`${td} font-mono text-[13px]`}>{new Date(s.started_at).toLocaleString('en-GB')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            </details>
          )}
        </DataState>
      </Section>
    </>
  )
}
