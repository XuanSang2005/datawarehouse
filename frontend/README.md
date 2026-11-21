# frontend/: React + Vite + TypeScript + Tailwind CSS

The UI for decision makers, following the prototype in `docs/design/prototype/` ("Maré Revenue Desk").
Every `/api/*` request is proxied by Vite to the backend (port `BACKEND_PORT` in the root `.env`).

```
src/
├── main.tsx             Entry point (Router + FiltersProvider)
├── App.tsx              Router + layout
├── routes.tsx           ★ List of pages (the nav bar is generated from it)
├── pages/               One page = one *Page.tsx file
├── components/
│   ├── layout/          Page frame: top bar (logo, menu, hotel picker), footer
│   ├── common/          ledger.tsx (Section, Focal, KpiStrip, Tabs, BarCell...), DataState, ErrorBox
│   ├── charts/          LedgerLineChart (Recharts), ColumnBars
│   └── filters/         FilterBar (arrival dates, channel, country)
├── context/             Filters shared by every page
├── api/
│   ├── client.ts        Shared fetch + error normalisation (ApiError, with the backend's hint)
│   └── endpoints.ts     ★ One function per backend endpoint
├── hooks/               useApi (data / error / loading, refetches when deps change), useDebounced, useToast
├── lib/                 format.ts (en-GB numbers and dates, EUR), theme.ts (hex colours for SVG)
├── types/api.ts         ★ Data types, MUST match backend/app/schemas
└── styles/global.css    Tailwind + design tokens (@theme)
```

## Run
```bash
npm install
```
```bash
npm run dev
```
Open http://localhost:5173 (the backend must be running on port 8000).

## Check before pushing
```bash
npm run lint && npm run build
```

## Adding a page
`types/api.ts` → `api/endpoints.ts` → `pages/XxxPage.tsx` → add one line to `routes.tsx`.

## UI conventions
- Style with Tailwind utility classes in TSX. Use colour tokens: `bg-rifle`, `text-oyster-ink`, `border-kangaroo`...
  (declared in `styles/global.css`). Do not add per-page CSS files.
- `rust` (brick red) is **only** for cancellations / negative values; `rifle` for City Hotel, `brass` for Resort Hotel.
- Each page has exactly one `<Focal>` block (Rifle-green background) as its focal point; sections are separated by `<Section>` (top rule).
- No KPI calculations in the frontend: rates/ADR/what-if come from the backend; the frontend only formats them with `lib/format.ts`.
- Wrap every data block in `<DataState>` for consistent loading / error / empty states.
