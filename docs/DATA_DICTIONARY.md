# Data Dictionary

> **Rule:** whenever you add or modify a table, update this file in the **same PR**.

## 1. Source: `hotel_bookings.csv` → `bronze.hotel_bookings`

Source: Antonio, Almeida & Nunes (2019), *Hotel booking demand datasets*, Data in Brief 22, 41–49.
Grain: **1 row = 1 booking**. 119,390 rows, 32 columns. In bronze, every column is `TEXT`.

| Column | Meaning | Values / notes |
|---|---|---|
| `hotel` | Hotel | `City Hotel`, `Resort Hotel` |
| `is_canceled` | Whether the booking was cancelled | `1` = cancelled, `0` = not cancelled |
| `lead_time` | Number of days from booking to arrival | |
| `arrival_date_year` / `_month` / `_week_number` / `_day_of_month` | Arrival date | Month written as an English word (`July`) |
| `stays_in_weekend_nights` | Number of weekend nights (Sat, Sun) stayed or booked | |
| `stays_in_week_nights` | Number of weeknights (Mon–Fri) | |
| `adults`, `children`, `babies` | Number of adults / children / babies | `children` contains `NA` values |
| `meal` | Meal plan | `BB` bed & breakfast, `HB` half board, `FB` full board, `SC`/`Undefined` no meal |
| `country` | Guest's country | ISO 3166-1 alpha-3 code; contains `NULL` values |
| `market_segment` | Market segment | `TA` = travel agents, `TO` = tour operators, `Direct`, `Corporate`, `Groups`… |
| `distribution_channel` | Distribution channel | `TA/TO`, `Direct`, `Corporate`, `GDS` |
| `is_repeated_guest` | Returning guest | `1` / `0` |
| `previous_cancellations` | Number of the guest's previous cancellations | |
| `previous_bookings_not_canceled` | Number of previous bookings not cancelled | |
| `reserved_room_type` | Reserved room type | Anonymized code (A, B, C…) |
| `assigned_room_type` | Room type actually assigned | ⚠ May contain information known only after booking (leakage risk) |
| `booking_changes` | Number of changes to the booking until check-in/cancellation | ⚠ Leakage risk |
| `deposit_type` | Deposit type | `No Deposit`, `Non Refund`, `Refundable` |
| `agent` | Agent ID | Contains `NULL` |
| `company` | ID of the company that booked/paid | Mostly `NULL` |
| `days_in_waiting_list` | Days on the waiting list before confirmation | |
| `customer_type` | Customer type | `Transient`, `Transient-Party`, `Contract`, `Group` |
| `adr` | Average Daily Rate = total lodging amount / number of nights | EUR |
| `required_car_parking_spaces` | Number of car parking spaces requested | |
| `total_of_special_requests` | Number of special requests | |
| `reservation_status` | Final status | `Canceled`, `Check-Out`, `No-Show`. ⛔ **Leakage**: never use as a feature |
| `reservation_status_date` | Date of the final status | ⛔ **Leakage** |

Technical columns added in bronze: `_source_row` (row number in the file), `_source_file`, `_loaded_at`.

## 2. `silver.hotel_bookings`

Grain: **1 row = 1 booking**. Primary key: `booking_id`.

| Column | Type | Source / derivation |
|---|---|---|
| `booking_id` | BIGINT | `_source_row` (the original dataset has no ID) |
| `hotel_name` | TEXT | `hotel` |
| `is_canceled` | BOOLEAN | `is_canceled = '1'` |
| `lead_time` | INT | |
| `arrival_date` | DATE | combines year + month + day_of_month |
| `booking_date` | DATE | `arrival_date - lead_time` |
| `arrival_week_number` | INT | |
| `weekend_nights`, `week_nights` | INT | |
| `total_nights` | INT | `weekend_nights + week_nights` |
| `departure_date` | DATE | `arrival_date + total_nights` |
| `adults`, `children`, `babies` | INT | `children`: `NA` → 0 |
| `total_guests` | INT | `adults + children + babies` |
| `party_type` | TEXT | `Other` (0 adults) / `Family` (with children or babies) / `Solo` (1 adult) / `Couple` (2) / `Group` (≥ 3) |
| `meal` | TEXT | `Undefined` → `SC` |
| `country_code` | TEXT | `NULL`/`NA` → NULL; `CN` → `CAN` (Canada), `TMP` → `TLS` (East Timor) |
| `market_segment`, `distribution_channel` | TEXT | `Undefined` → NULL |
| `is_repeated_guest` | BOOLEAN | |
| `previous_cancellations`, `previous_bookings_not_canceled` | INT | |
| `reserved_room_type`, `assigned_room_type` | TEXT | |
| `booking_changes`, `days_in_waiting_list` | INT | |
| `deposit_type`, `customer_type` | TEXT | |
| `agent_id`, `company_id` | INT | `NULL` → NULL |
| `adr` | NUMERIC(10,2) | |
| `required_car_parking_spaces`, `total_of_special_requests` | INT | |
| `reservation_status` | TEXT | ⛔ leakage |
| `reservation_status_date` | DATE | ⛔ leakage |

**Data quality issues found** (`database/checks/`, not filtered in silver):

| Check | Rows | Handling in gold (agreed) |
|---|---|---|
| No guests (0 adults, 0 children, 0 babies) | 180 | Removed from `fact_booking` |
| Negative ADR | 1 | Removed from `fact_booking` |
| 0 nights stayed | 715 | Kept; ADR is computed from totals, so it is unaffected |
| `country_code` NULL | 488 | Assigned `country_key = -1` (Unknown) in `dim_country` |

## 3. `bronze.pt_holidays` → `silver.pt_holidays`

Grain: **1 row = 1 public holiday** (names are merged when two holidays fall on the same date). Years 2013–2018. Generated with the `holidays` library (country code `PT`).

| Column | Type (silver) | Meaning |
|---|---|---|
| `holiday_date` | DATE (PK) | Holiday date |
| `holiday_name` | TEXT | Holiday name (in Portuguese) |

## 4. `bronze.countries` → `silver.countries`

Source: [lukes/ISO-3166-Countries-with-Regional-Codes](https://github.com/lukes/ISO-3166-Countries-with-Regional-Codes) (`all/all.csv`, CC BY-SA 4.0).
Grain: **1 row = 1 country/territory** (249 rows). Bronze keeps the CSV column names as is (with hyphens).

| Column (silver) | Type | Source |
|---|---|---|
| `country_code` | TEXT (PK) | `alpha-3` |
| `country_code_alpha2` | TEXT | `alpha-2` |
| `country_name` | TEXT | `name` |
| `region` | TEXT | `region` (UN M49 continent); TWN → Asia, ATA → Antarctica added |
| `sub_region` | TEXT | `sub-region` |

## 5. `bronze.weather_daily` → `silver.weather_daily`

Source: [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) (ERA5 model, CC BY 4.0), downloaded by `etl/extract/weather.py`.
Grain: **1 row = 1 location × 1 day**, PK `(location, weather_date)`. 2 locations × 1,096 days (2015-01-01 → 2017-12-31) = **2,192 rows**.
Bronze keeps the API variable names as is (every column TEXT; API null values are empty strings). Dates follow `Europe/Lisbon` time.

| Column (silver) | Type | Source (bronze) | Meaning |
|---|---|---|---|
| `location` | TEXT (PK) | `location` | `Lisbon` (City Hotel) or `Faro` (Resort Hotel) |
| `weather_date` | DATE (PK) | `weather_date` | Date |
| `latitude`, `longitude` | NUMERIC(8,5) | `latitude`, `longitude` | Center of the grid cell returned by the API (a few km from the requested coordinates) |
| `weather_code` | SMALLINT | `weather_code` | WMO weather code |
| `temp_max_c`, `temp_min_c`, `temp_mean_c` | NUMERIC(4,1) | `temperature_2m_max/min/mean` | Temperature at 2 m (°C) |
| `precipitation_mm` | NUMERIC(6,1) | `precipitation_sum` | Total rain + snow (mm) |
| `rain_mm` | NUMERIC(6,1) | `rain_sum` | Rainfall (mm) |
| `precipitation_hours` | NUMERIC(4,1) | `precipitation_hours` | Hours with precipitation |
| `wind_speed_max_kmh` | NUMERIC(5,1) | `wind_speed_10m_max` | Maximum wind speed at 10 m (km/h) |
| `sunshine_hours` | NUMERIC(5,2) | `sunshine_duration` (seconds) ÷ 3600 | Sunshine hours |

## 6. Gold

Full design (rationale, formulas, ERD): [`STAR_SCHEMA.md`](STAR_SCHEMA.md). Convention: `-1` = Unknown, `0` = not applicable; FKs in facts are never NULL.

### `gold.business_assumptions`: assumed parameters (1 row = 1 parameter)
| Column | Meaning |
|---|---|
| `param_name` (PK) | Parameter name. Currently `non_refund_deposit_rate` = 0.20 |
| `param_value`, `unit`, `description` | Value, unit, description |

### Dimensions

| Table | Grain (row count) | Columns |
|---|---|---|
| `dim_date` | 1 day, 2013–2018 (2,191) | `date_key` (PK, YYYYMMDD), `full_date`, `day_of_month`, `day_of_week` (ISO 1–7), `day_name`, `is_weekend`, `iso_week`, `iso_year`, `week_start_date`, `month`, `month_name`, `quarter`, `year`, `year_month`, `season` (High/Shoulder/Low), `is_holiday`, `holiday_name` |
| `dim_hotel` | 1 hotel (2) | `hotel_key` (PK), `hotel_name`, `hotel_type`, `city`, `country_code`, `latitude`, `longitude`, `weather_location` (`Lisbon` / `Faro`, join key to `silver.weather_daily`) |
| `dim_country` | 1 country code + Unknown (178) | `country_key` (PK, -1 = Unknown), `country_code`, `country_name`, `region`, `sub_region`, `is_domestic`, `market_group` (Domestic / Core Europe / Other Europe / Rest of World / Unknown) |
| `dim_channel` | 1 segment × channel combination (26) | `channel_key` (PK), `market_segment`, `distribution_channel`, `channel_group` (OTA / Offline TA/TO / Direct / Corporate / Groups / Other), `is_intermediated` |
| `dim_room_type` | 1 room code (12) | `room_type_key` (PK), `room_type_code`, `room_type_label` |
| `dim_agent` | 1 agent + "No agent" (334) | `agent_key` (PK, 0 = no agent), `agent_id`, `agent_label`, `has_agent`, `valid_from`, `valid_to`, `is_current` |
| `dim_booking_profile` | 1 junk combination (154) | `booking_profile_key` (PK), `meal`, `meal_name`, `deposit_type`, `customer_type`, `is_repeated_guest`, `party_type` |

### `gold.fact_booking`: 1 row = 1 booking (119,209 rows)

| Group | Columns |
|---|---|
| Keys | `booking_id` (PK, degenerate), `hotel_key`, `booking_date_key`, `arrival_date_key`, `departure_date_key`, `status_date_key` ⛔, `country_key`, `channel_key`, `agent_key`, `reserved_room_type_key`, `assigned_room_type_key` ⚠, `booking_profile_key` |
| Degenerate | `company_id`, `reservation_status` ⛔ |
| Counts | `booking_count` (=1), `is_canceled` (0/1), `lead_time`, `weekend_nights`, `week_nights`, `total_nights`, `room_nights_sold` ⛔, `adults`, `children`, `babies`, `guests` |
| Money (EUR) | `adr` (non-additive), `booked_revenue` = adr × total_nights, `realized_revenue` ⛔ (not cancelled), `lost_revenue` ⛔ (cancelled, gross), `deposit_retained` ⛔ (cancelled + Non Refund × deposit rate), `net_lost_revenue` ⛔ = lost − deposit |
| Behavior | `days_in_waiting_list`, `previous_cancellations`, `previous_bookings_not_canceled`, `total_of_special_requests`, `required_car_parking_spaces`, `booking_changes` ⚠, `is_room_changed` ⚠, `cancel_lead_days` ⛔ |

⛔ = derived from the cancellation outcome, must never be used as an ML feature. ⚠ = use with caution (known only after booking).

### `gold.fact_daily_occupancy`: 1 row = 1 hotel × 1 night (1,586 rows, 2015-07-01 → 2017-08-31)

| Column | Meaning |
|---|---|
| `hotel_key`, `stay_date_key` | PK, FK |
| `rooms_occupied` | Number of non-cancelled bookings that include this night |
| `rooms_canceled` | Number of cancelled bookings that would have included this night |
| `rooms_booked` | `rooms_occupied + rooms_canceled` |
| `guests_in_house` | Number of guests staying this night |
| `arrivals`, `departures` | Arrivals / check-outs (non-cancelled bookings) |
| `realized_revenue`, `lost_revenue` | Sum of `adr` of non-cancelled / cancelled bookings on this night |

### `gold.fact_daily_weather`: 1 row = 1 hotel × 1 day (2,192 rows, 2015-01-01 → 2017-12-31)

Joins 1:1 with `fact_daily_occupancy` (`hotel_key`, `stay_date_key = date_key`) and N:1 from `fact_booking` (`hotel_key`, `arrival_date_key = date_key`), without duplicating fact rows.

| Column | Meaning |
|---|---|
| `hotel_key`, `date_key` | PK, FK |
| `weather_code`, `weather_group` | WMO code and group: `Clear`, `Cloudy`, `Fog`, `Drizzle`, `Rain`, `Snow`, `Thunderstorm`, `Unknown` |
| `temp_max_c`, `temp_min_c`, `temp_mean_c` | Temperature (°C), non-additive |
| `precipitation_mm`, `rain_mm`, `precipitation_hours` | Precipitation (mm), hours of precipitation |
| `wind_speed_max_kmh`, `sunshine_hours` | Maximum wind speed (km/h), sunshine hours |
| `is_rainy_day` | 0/1, `precipitation_mm >= 1`. ⛔ not to be used as a cancellation prediction feature (unknown at booking time) |

### KPI views

| View | Grain | Specific columns (besides the common set) |
|---|---|---|
| `kpi_monthly_hotel` | hotel × arrival month | `year`, `quarter`, `month`, `year_month` |
| `kpi_channel` | hotel × `channel_group` × arrival month | `channel_group`, `year`, `month`, `year_month` |
| `kpi_country` | hotel × country × arrival year | `country_code`, `country_name`, `region`, `market_group`, `year` |
| `kpi_cancellation_profile` | hotel × lead time band × `deposit_type` × `channel_group` | `lead_time_band`, `lead_time_band_order`, `deposit_type`, `channel_group` |
| `kpi_daily_occupancy_weather` | hotel × night (1,586) | `stay_date`, `day_of_week`, `is_weekend`, `is_holiday`, `holiday_name`, `season`, the measures of `fact_daily_occupancy`, `adr`, `weather_group`, `temp_max_c`, `temp_mean_c`, `precipitation_mm`, `sunshine_hours`, `wind_speed_max_kmh`, `is_rainy_day` |
| `kpi_weekly_occupancy` | hotel × ISO week | `iso_year`, `iso_week`, `week_start_date`, `days_in_week`, `is_complete_week`, `room_nights_sold`, `room_nights_canceled`, `room_nights_booked`, `guest_nights`, `arrivals`, `realized_revenue`, `lost_revenue`, `adr`, `night_cancellation_rate` |

Common column set of the first 4 views: `bookings`, `canceled_bookings`, `cancellation_rate`, `room_nights_sold`, `realized_revenue`,
`lost_revenue`, `net_lost_revenue`, `adr`, `avg_lead_time`, `avg_los`. Rates and ADR are all recomputed from totals.

### ML result tables (`ml_*`)

Created (DDL in `database/ml/`, idempotent, not run by `etl/run_pipeline.py`) and written by the scripts in `ml/`.
Column contract: [`STAR_SCHEMA.md`](STAR_SCHEMA.md) section 7. Model details: [`ml/README.md`](../ml/README.md).

#### `gold.ml_booking_risk`: 1 row = 1 booking × 1 model version (119,209 rows with `cancellation_v1`)
Written by `python -m ml.cancellation.train` (deletes the rows with the same `model_version`, then writes them again).

| Column | Type | Meaning |
|---|---|---|
| `booking_id` | BIGINT (PK) | = `gold.fact_booking.booking_id`. No FK declared (gold uses DROP CASCADE); join with `JOIN ... USING (booking_id)` |
| `model_version` | TEXT (PK) | Version of the scoring model, e.g. `cancellation_v1` (model `cancellation_gbm`) |
| `cancel_probability` | NUMERIC(5,4) | Predicted cancellation probability, 0–1 |
| `risk_band` | TEXT | `Low` / `Medium` / `High` based on the `threshold_medium`, `threshold_high` thresholds in `ml_model_metrics` (v1: 0.17 and 0.31) |
| `is_test_set` | BOOLEAN | TRUE if `arrival_date` ≥ 2017-01-01 (not seen by the model during training). FALSE: in-sample score, more optimistic than reality |
| `scored_at` | TIMESTAMPTZ | Scoring timestamp |

#### `gold.ml_model_metrics`: 1 row = 1 version × 1 model × 1 metric × 1 dataset (shared by E3, E4)
Each script only deletes/writes rows with its own `model_name`; it never DROPs the table.

| Column | Meaning |
|---|---|
| `model_version`, `model_name`, `metric_name`, `dataset` | PK. `dataset`: `train` / `validation` / `test` / `backtest`... |
| `metric_value` | NUMERIC(12,6) |
| `trained_at` | Training timestamp |

Metrics of the cancellation models (`model_name` = `cancellation_logreg`, `cancellation_gbm`, `cancellation_gbm_no_country`):
`auc`, `pr_auc`, `brier`, `precision`, `recall`, `f1`, `accuracy`, `tn`, `fp`, `fn`, `tp` (at the High threshold),
`precision_at_medium`, `recall_at_medium`, `f1_at_medium` (at the Medium threshold, test set only), `n_rows`, `positive_rate`;
`threshold_medium`, `threshold_high` (dataset `validation`); and for `cancellation_gbm` on test only:
`{low,medium,high}_{bookings,share,cancel_rate}` (risk band distribution and actual cancellation rate of each band).

#### `gold.ml_demand_forecast`: 1 row = 1 hotel × 1 week × 1 model version (252 rows)

Written by `python -m ml.forecast.train` (DDL: `database/ml/03_ml_demand_forecast.sql`), not created by the ETL pipeline.
Method details: [`ml/README.md`](../ml/README.md#e4-weekly-demand-forecasting).

| Column | Meaning |
|---|---|
| `hotel_key`, `week_start_date`, `model_version` | PK. `week_start_date` = the Monday that starts the week (matches `dim_date.week_start_date`) |
| `model_version` | `forecast_gbm_v1` (main model), `forecast_seasonal_naive_v1`, `forecast_moving_avg_v1` (baselines). Matches `ml_model_metrics.model_version` |
| `predicted_room_nights` | Forecast room-nights sold (non-cancelled bookings) for that week |
| `lower_bound`, `upper_bound` | 80% prediction interval (from the backtest error distribution by horizon) |
| `actual_room_nights` | Actual value; NULL for future weeks and for the week of 2017-08-28 (only 4/7 nights of data) |
| `horizon_weeks` | How many weeks ahead the forecast is: 1 for the 2017 backtest weeks, 1..8 for the 8 future weeks |
| `created_at` | Write timestamp |

Each model has 84 rows: 2 hotels × (34 backtest weeks 2017-01-02 → 2017-08-21 + 8 future weeks 2017-08-28 → 2017-10-16).
The corresponding metrics are in `gold.ml_model_metrics` with `model_name` starting with `forecast_`
(`mape`, `mape_h1`…`mape_h8`, `mape_<hotel>`, `mape_h1_<hotel>`, `interval_coverage_80`; `dataset` = `backtest` or
`calibration`). MAPE is stored as a ratio (0.0857 = 8.57%).

## 7. `meta.etl_run_log`

| Column | Meaning |
|---|---|
| `log_id` | Auto-increment key |
| `run_id` | UUID of one pipeline run |
| `step` | Step name, e.g. `silver/01_hotel_bookings.sql` |
| `status` | `running`, `success`, `warning`, `failed` |
| `rows_affected` | Rows loaded, or number of violating rows (for checks) |
| `message` | Error or warning message |
| `started_at`, `finished_at` | Timestamps |
