# backend/: FastAPI

The API reads data from the `gold` and `meta` schemas, applies the logic (what-if, recommendations) and returns JSON to the frontend.

```
backend/
├── app/
│   ├── main.py              App setup, centralized DB error handling (→ HTTP 503)
│   ├── api/
│   │   ├── router.py        Collects the routers, prefix /api
│   │   └── routes/          HTTP endpoints: NO SQL here
│   ├── services/            Business logic, calculations
│   ├── repositories/        SQL ONLY (reads gold/meta)
│   ├── schemas/             Pydantic models (contract with the frontend)
│   └── core/                config (.env), db (engine), logging
├── tests/
├── requirements.txt
└── Dockerfile
```

## Run
```bash
cd backend && uvicorn app.main:app --reload --port 8000
```
Swagger UI to try the API: http://localhost:8000/docs

## Available endpoints
Parameter and response details: Swagger UI `/docs`. Matching TypeScript types: `frontend/src/types/api.ts`.

**Shared filters** (endpoints marked ✓ in the Filter column): `hotel_key`, `date_from`, `date_to` (by **arrival date**),
`channel_group` (e.g. `OTA`), `country_code` (ISO alpha-3, `UNK` = unknown country).

| Method | Path | Filter | Description | Goal |
|---|---|---|---|---|
| GET | `/api/health` | | API status and DB connection | |
| GET | `/api/pipeline/runs?limit=50` | | Most recent ETL step logs | |
| GET | `/api/filters` | | Options for the FilterBar: hotels (with `peak_rooms_occupied`), channel groups, segments, countries, date range | |
| GET | `/api/kpi/summary` | ✓ | Overall KPIs + split by hotel (City vs Resort) | G1 |
| GET | `/api/kpi/timeseries?grain=year\|quarter\|month\|week&by_hotel=` | ✓ | KPI series for drill-down | G1 |
| GET | `/api/cancellation/breakdown?by=lead_time\|channel\|deposit_type\|country\|market_segment\|customer_type&top_n=` | ✓ | Cancellation rate by dimension | G2 |
| GET | `/api/cancellation/high-risk?risk_band=High\|Medium\|Low\|All&min_probability=&test_set_only=true&sort=probability\|expected_loss&page=&page_size=` | ✓ | High cancellation-risk bookings, paginated; includes `total`, `booked_revenue_total`, `expected_loss_total` across all pages | G2 |
| GET | `/api/cancellation/model-metrics` | | AUC, precision, recall, F1, thresholds of the cancellation model | G2 |
| GET | `/api/forecast?hotel_key=&model_version=` | | Weekly room-nights: forecast, 80% interval, actuals, history | G3 |
| GET | `/api/forecast/metrics` | | MAPE of the main model and the baseline | G3 |
| POST | `/api/what-if` | | Overbooking + risk-based deposit simulation, benefit curve, recommended level | G4 |
| GET | `/api/channels/ranking?sort_by=&top_n=&min_bookings=` | ✓ | Channel group ranking | G5 |
| GET | `/api/markets/ranking?sort_by=&top_n=&min_bookings=100` | ✓ | Country ranking | G5 |

**Error codes**: `404` + `hint` when data is not available yet (e.g. the ML script has not been run), `422` for invalid parameters, `503` on DB errors.

**Number conventions**: money is in EUR; rates are returned as 0–1; rates/ADR are computed from totals (`sum/sum`), `null` when the denominator is 0.

### What-if example
```bash
curl -s -X POST localhost:8000/api/what-if -H 'Content-Type: application/json' \
  -d '{"hotel_key": 1, "capacity": 230, "overbooking_pct": 0.05, "walk_cost": 150, "ota_commission": 0.15}'
```
By default the simulation runs on 2017 (the cancellation model's test set, out-of-sample risk scores). The default deposit
threshold is the model's `High` threshold (`gold.ml_model_metrics`); the default deposit rate comes from `gold.business_assumptions`.
Formulas: the docstring of `app/services/what_if_service.py`.

## Adding an endpoint
`schemas/` → `repositories/` → `services/` → `api/routes/` → include in `api/router.py` → `tests/`.
Remember to update `frontend/src/types/api.ts` to match the schema.
