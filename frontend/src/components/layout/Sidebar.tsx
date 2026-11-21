import { NavLink } from 'react-router-dom'
import { routes } from '../../routes'

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        Tourism DSS
        <small>Hotel revenue &amp; cancellation</small>
      </div>
      <nav>
        {routes.map((r) => (
          <NavLink key={r.path} to={r.path} end className="sidebar-link">
            {r.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
