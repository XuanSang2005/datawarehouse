import type { ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useFilters } from '../../context/filters'
import { routes } from '../../routes'
import { Cap, Segmented } from '../common/ledger'

/** Hotel picker shared by every page (values come from GET /api/filters). */
function HotelToggle() {
  const { options, filters, setFilters } = useFilters()
  const hotels = options?.hotels ?? []
  return (
    <Segmented<number | null>
      label="Hotel"
      value={filters.hotelKey}
      onChange={(v) => setFilters({ hotelKey: v })}
      options={[
        { value: null, label: 'Both' },
        ...hotels.map((h) => ({ value: h.hotel_key, label: h.hotel_type })),
      ]}
    />
  )
}

export default function AppLayout({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  const current = routes.find((r) => r.path === pathname)

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 bg-merino">
        <div className="mx-auto flex max-w-[1360px] flex-wrap items-center gap-x-9 gap-y-3 px-5 pt-[18px] pb-3.5">
          <NavLink to="/" className="flex items-baseline gap-2.5">
            <b className="font-display text-[28px] leading-none font-bold tracking-[0.06em]">MARÉ</b>
            <Cap className="max-sm:hidden">Lisbon · Algarve</Cap>
          </NavLink>
          <nav
            aria-label="Pages"
            className="order-3 flex min-w-0 basis-full gap-5 overflow-x-auto [scrollbar-width:none] md:order-none md:flex-1 md:basis-auto md:gap-[26px]"
          >
            {routes.map((r) => (
              <NavLink
                key={r.path}
                to={r.path}
                end
                className={({ isActive }) =>
                  `relative py-1.5 text-[15px] font-medium whitespace-nowrap transition-colors after:absolute after:inset-x-0 after:bottom-0 after:h-0.5 after:origin-left after:bg-rifle after:transition-transform after:duration-400 after:ease-ledger ${
                    isActive
                      ? 'text-cedar after:scale-x-100'
                      : 'text-oyster-ink after:scale-x-0 hover:text-cedar'
                  }`
                }
              >
                {r.label}
              </NavLink>
            ))}
          </nav>
          <div className={`ml-auto md:ml-0 ${current?.hotelFilter === false ? 'invisible' : ''}`}>
            <HotelToggle />
          </div>
        </div>
        {/* Double rule under the top bar */}
        <div className="mx-5 h-1 border-y border-cedar xl:mx-auto xl:max-w-[1320px]" />
      </header>

      <main className="mx-auto flex max-w-[1360px] flex-col gap-11 px-5 pt-[34px] pb-10 md:gap-14">
        {children}
      </main>

      <footer className="mx-auto max-w-[1360px] px-5 pt-6 pb-8">
        <div className="flex flex-wrap justify-between gap-3 border-t border-kangaroo pt-3.5">
          <Cap>Revenue Desk · reads gold & meta</Cap>
          <Cap>Hotel Booking Demand, Antonio et al. 2019</Cap>
        </div>
      </footer>
    </div>
  )
}
