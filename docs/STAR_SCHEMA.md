# Detailed Star Schema Design (Gold layer)

> Status: **AGREED and IMPLEMENTED** (2026-11-21). The decisions are in [section 9](#9-agreed-decisions).
> SQL: `database/gold/` (file list in [section 8](#8-implementation)). Short column descriptions: `docs/DATA_DICTIONARY.md` section 6.
>
> Every number in this document comes from a real pipeline run on `hotel_bookings.csv` (119,390 rows).

---

## 1. Design process (Kimball's 4 steps)

| Step | Decision |
|---|---|
| **1. Select the business process** | (a) **Booking**: a guest books, then may cancel or stay. (b) **Nightly stay**: which rooms are occupied on which night. (c) **Daily context**: the weather at each hotel every day (external source, Open-Meteo). |
| **2. Declare the grain** | `fact_booking`: **1 row = 1 booking**. `fact_daily_occupancy`: **1 row = 1 hotel × 1 stay night**. `fact_daily_weather`: **1 row = 1 hotel × 1 day**. |
| **3. Identify the dimensions** | Date (4 roles), hotel, country, sales channel, room type (2 roles), agent, booking profile (junk). |
| **4. Identify the measures** | Number of bookings, nights, guests, revenue (booked / realized / lost to cancellations), lead time, ADR (non-additive). Temperature, precipitation, sunshine hours (non-additive across time, except precipitation and the number of rainy days). |

### Bus matrix: which dimensions each fact uses

| Fact \ Dimension | date | hotel | country | channel | room_type | agent | booking_profile |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `fact_booking` | ✔ ×4 roles | ✔ | ✔ | ✔ | ✔ ×2 roles | ✔ | ✔ |
| `fact_daily_occupancy` | ✔ (stay night) | ✔ | | | | | |
| `fact_daily_weather` | ✔ (day) | ✔ | | | | | |
| `ml_booking_risk` (ml/) | via `booking_id` | | | | | | |
| `ml_demand_forecast` (ml/) | ✔ (week) | ✔ | | | | | |

`dim_date` and `dim_hotel` are **conformed dimensions**: all three facts share them, so the dashboard can combine (drill across)
"revenue by booking", "occupied rooms by night" and "weather by day" on the same time and hotel axes.
Public holidays need no fact of their own: they are the `is_holiday`, `holiday_name` attributes of `dim_date` (national holidays, applying to both hotels).

---

## 2. ERD

```mermaid
erDiagram
    dim_date ||--o{ fact_booking : "booking_date_key"
    dim_date ||--o{ fact_booking : "arrival_date_key"
    dim_date ||--o{ fact_booking : "departure_date_key"
    dim_date ||--o{ fact_booking : "status_date_key"
    dim_hotel ||--o{ fact_booking : "hotel_key"
    dim_country ||--o{ fact_booking : "country_key"
    dim_channel ||--o{ fact_booking : "channel_key"
    dim_room_type ||--o{ fact_booking : "reserved_room_type_key"
    dim_room_type ||--o{ fact_booking : "assigned_room_type_key"
    dim_agent ||--o{ fact_booking : "agent_key"
    dim_booking_profile ||--o{ fact_booking : "booking_profile_key"
    dim_date ||--o{ fact_daily_occupancy : "stay_date_key"
    dim_hotel ||--o{ fact_daily_occupancy : "hotel_key"
    dim_date ||--o{ fact_daily_weather : "date_key"
    dim_hotel ||--o{ fact_daily_weather : "hotel_key"

    fact_booking {
        bigint booking_id PK "degenerate dim"
        int hotel_key FK
        int booking_date_key FK
        int arrival_date_key FK
        int departure_date_key FK
        int status_date_key FK
        int country_key FK
        int channel_key FK
        int agent_key FK
        int reserved_room_type_key FK
        int assigned_room_type_key FK
        int booking_profile_key FK
        int company_id "degenerate dim"
        smallint booking_count
        smallint is_canceled
        int lead_time
        int total_nights
        numeric adr "non-additive"
        numeric booked_revenue
        numeric realized_revenue
        numeric lost_revenue
        numeric net_lost_revenue
    }
    fact_daily_occupancy {
        int hotel_key PK, FK
        int stay_date_key PK, FK
        int rooms_occupied
        int rooms_canceled
        int guests_in_house
        int arrivals
        int departures
        numeric realized_revenue
        numeric lost_revenue
    }
    fact_daily_weather {
        int hotel_key PK, FK
        int date_key PK, FK
        text weather_group
        numeric temp_max_c
        numeric temp_mean_c
        numeric precipitation_mm
        numeric sunshine_hours
        smallint is_rainy_day
    }
    dim_date {
        int date_key PK "YYYYMMDD"
        date full_date
        int year
        int quarter
        int month
        int iso_week
        boolean is_weekend
        boolean is_holiday
        text season
    }
    dim_hotel {
        int hotel_key PK
        text hotel_name
        text hotel_type
        text city
        text weather_location
    }
    dim_country {
        int country_key PK
        text country_code
        text country_name
        text region
        text market_group
    }
    dim_channel {
        int channel_key PK
        text market_segment
        text distribution_channel
        text channel_group
    }
    dim_room_type {
        int room_type_key PK
        text room_type_code
    }
    dim_agent {
        int agent_key PK
        int agent_id
        text agent_label
        boolean is_current
    }
    dim_booking_profile {
        int booking_profile_key PK
        text meal
        text deposit_type
        text customer_type
        boolean is_repeated_guest
        text party_type
    }
```

ASCII version (for slides):

```
                                ┌──────────────────────┐
                                │      dim_date        │  4 roles in fact_booking:
                                │ (role-playing)       │  booking / arrival / departure / status
                                └──────────┬───────────┘
   ┌──────────────┐                        │                        ┌──────────────┐
   │ dim_country  │──┐                     │                     ┌──│  dim_hotel   │ (conformed)
   └──────────────┘  │             ┌───────▼────────┐            │  └──────┬───────┘
   ┌──────────────┐  ├─────────────│  fact_booking  │────────────┤         │
   │ dim_channel  │──┤             │ 1 row=1 booking│            │  ┌──────┴───────┐
   └──────────────┘  │             └───────┬────────┘            ├──│dim_room_type │ (2 roles:
   ┌──────────────┐  │                     │                     │  └──────────────┘ reserved/assigned)
   │dim_booking_  │──┘                     │                     │  ┌──────────────┐
   │profile (junk)│                        │                     └──│  dim_agent   │ (SCD2-ready)
   └──────────────┘                        │ expand per night       └──────────────┘
                                ┌──────────▼───────────┐       ┌──────────────────────┐
                                │ fact_daily_occupancy │ 1 : 1 │  fact_daily_weather  │  1 row = 1 hotel × 1 day
                                │ (periodic snapshot)  │◀─────▶│  (Open-Meteo)        │  shares dim_date, dim_hotel
                                └──────────────────────┘       └──────────────────────┘
                                  1 row = 1 hotel × 1 night
```

---

## 3. General conventions

| Topic | Convention |
|---|---|
| **Surrogate key** | `INT`, generated with `ROW_NUMBER() OVER (ORDER BY <natural key>)`. Ordering by the natural key means **every full load produces the same keys** (stable for the `ml_*` tables and for FE bookmarks). Only `dim_date` uses the "smart" key `YYYYMMDD`. |
| **Special members** | `-1` = *Unknown* (missing in the source, e.g. `country` NULL). `0` = *Not applicable* (e.g. a booking without an agent). Facts **never** have NULL FKs. |
| **SCD** | Full load, so every dimension is **Type 1** (overwrite). `dim_agent` has Type 2 columns (`valid_from`, `valid_to`, `is_current`) ready, to illustrate how to extend it with incremental loading. |
| **Flags in dimensions** | `BOOLEAN`, named `is_*`. |
| **Flags used as measures in facts** | `SMALLINT` 0/1 (e.g. `is_canceled`), so that `SUM()` gives the number of cancelled bookings and works in any BI tool. |
| **Money** | `NUMERIC(12,2)`, in EUR. |
| **Constraints** | PKs on every table; FKs from facts to dims (they express integrity and are cheap with 119k rows); indexes on frequently filtered FKs (`hotel_key`, `arrival_date_key`). |
| **Idempotent** | `DROP TABLE IF EXISTS gold.x CASCADE;` then `CREATE TABLE ... AS SELECT`. `CASCADE` also drops dependent FKs/views; they are recreated because the fact (`3x`) and KPI (`5x`) files run later. |

---

## 4. Dimensions

### 4.1 `gold.dim_date`: role-playing, conformed

- **Source:** `generate_series('2013-01-01', '2018-12-31', '1 day')` + `silver.pt_holidays`.
  This range covers every date in the data: the earliest booking date is 2013-06-24, the latest departure date is 2017-09-14. It matches the year range of the holiday source.
- **Grain:** 1 row = 1 calendar day. **2,191 rows.**
- **Hierarchy:** Year → Quarter → Month → Day, and ISO Year → ISO Week → Day (2 branches, because a week can span 2 months).

| Column | Type | Example | Notes |
|---|---|---|---|
| `date_key` | INT PK | `20160815` | `YYYYMMDD` |
| `full_date` | DATE UNIQUE | `2016-08-15` | |
| `day_of_month` | SMALLINT | `15` | |
| `day_of_week` | SMALLINT | `1` | ISO: 1 = Monday … 7 = Sunday |
| `day_name` | TEXT | `Monday` | |
| `is_weekend` | BOOLEAN | `false` | Saturday, Sunday |
| `iso_week` | SMALLINT | `33` | **Computed from the date**, not taken from the source column (see note) |
| `iso_year` | SMALLINT | `2016` | Year of the ISO week (differs from `year` for the first/last days of the year) |
| `week_start_date` | DATE | `2016-08-15` | The Monday that starts the week; used as the axis for weekly forecasting |
| `month` | SMALLINT | `8` | |
| `month_name` | TEXT | `August` | |
| `quarter` | SMALLINT | `3` | |
| `year` | SMALLINT | `2016` | |
| `year_month` | TEXT | `2016-08` | Chart axis label, sortable |
| `season` | TEXT | `High` | `High` = 7–8; `Shoulder` = 4–6, 9–10; `Low` = 11–3. Based on the Resort's measured ADR: Aug ≈ €174, Jan ≈ €49 |
| `is_holiday` | BOOLEAN | `true` | Present in `silver.pt_holidays` |
| `holiday_name` | TEXT | `Assunção de Nossa Senhora` | Portuguese name (`holidays` library). NULL if not a holiday |

> ⚠ **Source quality notes (verified):**
> 1. The dataset's `arrival_date_week_number` column **does not match** the ISO week computed from the arrival date (100% mismatch in 2016, ~10% in 2015/2017). Therefore `dim_date` computes the week itself, and the source column is **not carried into gold**.
> 2. The dataset's split into `stays_in_weekend_nights` / `stays_in_week_nights` **does not match** the weekday of the arrival date (e.g. a 1-night booking arriving on a Monday is counted as a weekend night). Therefore these two measures are **kept as in the source** in `fact_booking`, not recomputed from `dim_date`, and not cross-checked against `is_weekend`.

**4 roles in `fact_booking`:**

| FK in the fact | Meaning | Analytical question |
|---|---|---|
| `booking_date_key` | Date the guest booked (`arrival_date - lead_time`) | When do bookings come in? Booking pace? |
| `arrival_date_key` | Planned arrival date | Seasonality, revenue by stay period (**the dashboard's default time axis**) |
| `departure_date_key` | Check-out date (`arrival_date + total_nights`) | Check-outs per day |
| `status_date_key` | Date of the final status (cancellation date or check-out date) | When are bookings cancelled? ⛔ Descriptive use only, **never for ML** |

In the dashboard and the views, each role is used through an alias: `JOIN gold.dim_date AS arr ON arr.date_key = f.arrival_date_key`.

### 4.2 `gold.dim_hotel`: conformed

- **Source:** `SELECT DISTINCT hotel_name FROM silver.hotel_bookings` + descriptive attributes from the original paper. **2 rows.**

| Column | Type | City Hotel | Resort Hotel |
|---|---|---|---|
| `hotel_key` | INT PK | `1` | `2` |
| `hotel_name` | TEXT UNIQUE | `City Hotel` | `Resort Hotel` |
| `hotel_type` | TEXT | `City` | `Resort` |
| `city` | TEXT | `Lisbon` | `Algarve` |
| `country_code` | TEXT | `PRT` | `PRT` |
| `latitude`, `longitude` | NUMERIC(8,5) | Lisbon | Faro (Algarve) |
| `weather_location` | TEXT | `Lisbon` | `Faro` |

- `weather_location` is the hotel's weather location, the join key to `silver.weather_daily.location`
  (coordinates identical to `etl/extract/weather.py`). Used in `fact_daily_weather`.
- **Deliberately no room count column:** the dataset has no capacity (rule 10 in `CLAUDE.md`). Occupancy and RevPAR are computed in the backend from a user-entered parameter.

### 4.3 `gold.dim_country`

- **Source:** the country codes appearing in `silver.hotel_bookings`, LEFT JOIN with the ISO 3166 code table (**new source**, see section 8, step 0).
- **Grain:** 1 row = 1 country code. **177 codes + 1 Unknown row (`-1`) = 178 rows.**

| Column | Type | Example | Notes |
|---|---|---|---|
| `country_key` | INT PK | `128` | `-1` = Unknown (`country` NULL: 488 bookings in silver, 478 after filtering) |
| `country_code` | TEXT UNIQUE | `PRT` | ISO 3166-1 alpha-3 (natural key) |
| `country_name` | TEXT | `Portugal` | Falls back to the code itself when not found in the ISO table |
| `region` | TEXT | `Europe` | Continent (UN M49 regions) |
| `sub_region` | TEXT | `Southern Europe` | |
| `is_domestic` | BOOLEAN | `true` | `country_code = 'PRT'` |
| `market_group` | TEXT | `Domestic` | `Domestic` (PRT) / `Core Europe` (GBR, FRA, ESP, DEU, ITA, IRL, BEL, NLD) / `Other Europe` / `Rest of World` / `Unknown`. Serves Sales & Marketing (objective G5) |

> Two non-standard codes in the source are normalized in **silver** (`silver/01_hotel_bookings.sql`):
> `CN` (1,279 bookings) → `CAN` (Canada; agreed by the team in Q2, since `CHN` already exists separately and the dataset has no `CAN`),
> `TMP` (3 bookings, the old code for East Timor) → `TLS`. After normalization, every code exists in the ISO table.
>
> Booking distribution by `market_group`: Core Europe 49,945, Domestic 48,483, Rest of World 11,067, Other Europe 9,236, Unknown 478.

### 4.4 `gold.dim_channel`: sales channel

- **Source:** the `(market_segment, distribution_channel)` combinations present in silver. **26 combinations** (including those with `Undefined`, which became NULL in silver and are shown as `Unknown`).
- **Why merge 2 columns into 1 dimension:** the two columns are strongly correlated (e.g. `Online TA` goes with `TA/TO` 99% of the time), the number of combinations is small, and users always filter them together.

| Column | Type | Example | Notes |
|---|---|---|---|
| `channel_key` | INT PK | `21` | |
| `market_segment` | TEXT | `Online TA` | `Unknown` if NULL |
| `distribution_channel` | TEXT | `TA/TO` | `Unknown` if NULL |
| `channel_group` | TEXT | `OTA` | Grouping for the dashboard: `OTA` (Online TA), `Offline TA/TO`, `Direct`, `Corporate`, `Groups`, `Other` (Complementary, Aviation, Unknown) |
| `is_intermediated` | BOOLEAN | `true` | `distribution_channel IN ('TA/TO', 'GDS')`: commission is paid. Used for the channel cost what-if |

UNIQUE `(market_segment, distribution_channel)`.

### 4.5 `gold.dim_room_type`: role-playing (2 roles)

- **Source:** `UNION` of `reserved_room_type` and `assigned_room_type`. **12 codes**: A, B, C, D, E, F, G, H, I, K, L, P (I and K appear only as assigned rooms).

| Column | Type | Example |
|---|---|---|
| `room_type_key` | INT PK | `1` |
| `room_type_code` | TEXT UNIQUE | `A` |
| `room_type_label` | TEXT | `Room type A` (codes are anonymized in the source; real names are unknown) |

Roles in the fact: `reserved_room_type_key` (type the guest booked) and `assigned_room_type_key` (type actually assigned).
14,917 bookings were assigned a different type than booked.
⚠ `assigned_room_type` is only known when the guest arrives, so it is **not used as a cancellation prediction feature**.

### 4.6 `gold.dim_agent`: SCD Type 2-ready

- **Source:** `DISTINCT agent_id` from silver. **333 agent IDs + 1 row `0` "No agent" = 334 rows.**

| Column | Type | Example | Notes |
|---|---|---|---|
| `agent_key` | INT PK | `9` | `0` = no agent (`agent` NULL) |
| `agent_id` | INT | `9` | Natural key (anonymized). NULL in row `0` |
| `agent_label` | TEXT | `Agent 9` | |
| `has_agent` | BOOLEAN | `true` | |
| `valid_from` | DATE | `1900-01-01` | Full load: every row is valid from the beginning |
| `valid_to` | DATE | `9999-12-31` | |
| `is_current` | BOOLEAN | `true` | |

The source has no agent attributes that change over time, so the SCD2 columns are currently constants.
How to use them after switching to incremental loading (e.g. if a changing `commission_rate` is added): close the old row (`valid_to`, `is_current = false`),
add a new row with a new `agent_key`, and let the fact look up the key by `booking_date BETWEEN valid_from AND valid_to`.

`company_id` (353 values, mostly NULL, no attributes) **is not a separate dimension**: it stays in the fact as a degenerate dimension.

### 4.7 `gold.dim_booking_profile`: junk dimension

- **Purpose:** groups low-cardinality flags and codes that would otherwise widen the fact or produce many tiny dimensions.
- **Source:** `DISTINCT` combinations **present in the data** (`silver.hotel_bookings`, including rows removed from the fact). **154 rows** (theoretical maximum: 4 × 3 × 4 × 2 × 5 = 480).
- `party_type` is precomputed in silver so that the fact and the dimension share one definition.

| Column | Type | Values |
|---|---|---|
| `booking_profile_key` | INT PK | |
| `meal` | TEXT | `BB`, `HB`, `FB`, `SC` |
| `meal_name` | TEXT | `Bed & Breakfast`, `Half Board`, `Full Board`, `Self Catering` |
| `deposit_type` | TEXT | `No Deposit`, `Non Refund`, `Refundable` |
| `customer_type` | TEXT | `Transient`, `Transient-Party`, `Contract`, `Group` |
| `is_repeated_guest` | BOOLEAN | |
| `party_type` | TEXT | Derived from guest counts: `Solo` (1 adult), `Couple` (2 adults), `Family` (with children or babies), `Group` (≥ 3 adults), `Other` (0 adults) |

UNIQUE on the 5 attribute columns. `party_type` distribution: Couple 81,559, Solo 22,577, Family 9,109, Group 5,741, Other 223.

---

## 5. Facts

### 5.1 `gold.fact_booking`: transaction fact

- **Source:** `silver.hotel_bookings`, JOINed with the dimensions to obtain the surrogate keys.
- **Grain:** **1 row = 1 booking.** PK = `booking_id` (degenerate dimension, traceable back to `bronze._source_row`).
- **Filtering of anomalous data** (decided in gold, see `DATA_DICTIONARY.md` section 2):

| Condition | Rows | Handling |
|---|---|---|
| No guests (`adults + children + babies = 0`) | 180 | **Removed** |
| Negative ADR | 1 | **Removed** |
| 0 nights stayed | 715 | **Kept.** Revenue = 0 and nights = 0, so ADR computed from totals (`sum(revenue)/sum(nights)`) is **automatically** unaffected |
| `country` NULL | 488 (478 after filtering the 2 rows above) | **Kept**, assigned `country_key = -1` |
| ADR = €5,400 (1 cancelled booking) | 1 | **Kept** (a real, cancelled booking, not included in realized revenue). A warning check flags ADR > 1,000 |

→ **119,209 rows** (119,390 − 181).

**Foreign keys**

| Column | References | Lookup |
|---|---|---|
| `hotel_key` | `dim_hotel` | `hotel_name` |
| `booking_date_key` | `dim_date` | `to_char(booking_date, 'YYYYMMDD')::INT` |
| `arrival_date_key` | `dim_date` | `arrival_date` |
| `departure_date_key` | `dim_date` | `arrival_date + total_nights` |
| `status_date_key` | `dim_date` | `reservation_status_date` ⛔ |
| `country_key` | `dim_country` | `country_code`, NULL → `-1` |
| `channel_key` | `dim_channel` | `(market_segment, distribution_channel)`, NULLs matched with `COALESCE(..., 'Unknown')` |
| `agent_key` | `dim_agent` | `agent_id`, NULL → `0` |
| `reserved_room_type_key` | `dim_room_type` | `reserved_room_type` |
| `assigned_room_type_key` | `dim_room_type` | `assigned_room_type` ⚠ |
| `booking_profile_key` | `dim_booking_profile` | the 5 columns of the junk dimension |

**Degenerate dimensions:** `booking_id` (PK), `company_id` (NULL allowed), `reservation_status` ⛔ (`Check-Out` / `Canceled` / `No-Show`, to distinguish cancellations from no-shows).

**Measures**

| Column | Type | Formula (from silver) | Additivity | Notes |
|---|---|---|---|---|
| `booking_count` | SMALLINT | `1` | Additive | Counts bookings with `SUM`, convenient for BI |
| `is_canceled` | SMALLINT | `is_canceled::INT` | Additive | Includes No-Shows (1,207). `SUM` = number of cancelled bookings |
| `lead_time` | INT | | Non-additive | Averages / percentiles only |
| `weekend_nights`, `week_nights` | INT | kept as in the source | Additive | See the note in 4.1 |
| `total_nights` | INT | `weekend + week` | Additive | Nights **booked** (room-nights booked) |
| `room_nights_sold` | INT | `total_nights` if not cancelled, otherwise `0` | Additive | |
| `adults`, `children`, `babies` | INT | | Additive | |
| `guests` | INT | `adults + children + babies` | Additive | |
| `adr` | NUMERIC(10,2) | kept as in the source | **Non-additive** | ⛔ Never `SUM(adr)` or `AVG(adr)`; use `SUM(realized_revenue) / NULLIF(SUM(room_nights_sold), 0)` |
| `booked_revenue` | NUMERIC(12,2) | `adr × total_nights` | Additive | Booking value at booking time (including bookings later cancelled) |
| `realized_revenue` | NUMERIC(12,2) | `booked_revenue` if not cancelled, otherwise `0` | Additive | **Realized revenue** (defined in `GLOSSARY.md`) |
| `lost_revenue` | NUMERIC(12,2) | `booked_revenue` if cancelled, otherwise `0` | Additive | **Gross loss from cancellations** (upper bound) |
| `deposit_retained` | NUMERIC(12,2) | `booked_revenue × non_refund_deposit_rate` if cancelled **and** `deposit_type = 'Non Refund'`, otherwise `0` | Additive | Deposit kept by the hotel. Default **20%** (Q3), taken from `gold.business_assumptions` |
| `net_lost_revenue` | NUMERIC(12,2) | `lost_revenue − deposit_retained` | Additive | **Net loss after the retained deposit** |
| `days_in_waiting_list` | INT | | Non-additive | |
| `previous_cancellations`, `previous_bookings_not_canceled` | INT | | Non-additive | Guest history; usable as ML features |
| `total_of_special_requests`, `required_car_parking_spaces` | INT | | Additive | |
| `booking_changes` | INT | | Additive | ⚠ Leakage risk for ML |
| `is_room_changed` | SMALLINT | `reserved <> assigned` | Additive | ⚠ Known only on arrival, leakage risk |
| `cancel_lead_days` | INT | `arrival_date - reservation_status_date` if cancelled, otherwise NULL | Non-additive | ⛔ How long before arrival the booking was cancelled. Answers "cancelled too close to arrival to resell". Median = 54 days, 10% cancel within 4 days |

Total reconciliation (real run): booked €42.71M = realized €25.99M + lost €16.73M. Lost €16.73M = retained deposits €0.72M + net lost €16.01M.
`SUM(room_nights_sold)` = 254,282, overall ADR = €102.20, cancellation rate = 37.08% (City 41.8%, Resort 27.8%).

**Indexes:** PK `booking_id`; indexes on `(hotel_key, arrival_date_key)`, `booking_date_key`, `channel_key`, `country_key`.

**Which columns may be used as ML features?** Rule 7 in `CLAUDE.md`:

| Group | Columns |
|---|---|
| ✅ Allowed (known at booking time) | `lead_time`, arrival date (month, week, `is_holiday`), number of nights, number of guests, `hotel`, `country`, `channel`, `agent`, `reserved_room_type`, the whole junk profile, `previous_*`, `days_in_waiting_list`, `adr`, `total_of_special_requests`, `required_car_parking_spaces` |
| ⚠ Use with great care | `booking_changes`, `assigned_room_type_key`, `is_room_changed` |
| ⛔ Forbidden | `status_date_key`, `reservation_status`, `cancel_lead_days`, `realized_revenue`, `lost_revenue`, `deposit_retained`, `net_lost_revenue`, `room_nights_sold` (all derived from the cancellation outcome). Actual weather on the arrival date (`fact_daily_weather`): unknown at booking time |

### 5.2 `gold.fact_daily_occupancy`: periodic snapshot

- **Purpose:** know **how many rooms are occupied each night** at each hotel. `fact_booking` cannot answer this directly,
  because a 5-night booking spans 5 different dates. This is the input for demand forecasting (G3) and the overbooking what-if (G4).
- **Source:** `gold.fact_booking` "expanded" per night: `generate_series(arrival_date, departure_date - 1)`, then grouped by hotel × night.
  RIGHT JOIN with `dim_hotel × dim_date` to make it **dense** (nights without guests still get a row, with value 0).
- **Grain:** **1 row = 1 hotel × 1 stay night.** PK `(hotel_key, stay_date_key)`.
- **Range:** nights from 2015-07-01 to 2017-08-31 (793 nights) → **1,586 rows**.
  After 2017-08-31 data is missing because the dataset has no arrivals from September 2017 onward, so the range is cut there.
  The first nights of July 2015 are slightly lower than in reality, because guests who arrived before 2015-07-01 and stayed over are missing. This note must go into the report.
- **Assumption:** 1 booking = 1 room (as described in the original dataset).

| Column | Type | Formula for each (hotel, night d) | Additivity |
|---|---|---|---|
| `hotel_key` | INT PK, FK | | |
| `stay_date_key` | INT PK, FK | | |
| `rooms_occupied` | INT | Number of **non-cancelled** bookings that include night d | Additive across hotels. Summed over time gives **room-nights sold** |
| `rooms_canceled` | INT | Number of **cancelled** bookings that would have included night d | Same as above. These are the "returned rooms", the basis for overbooking decisions |
| `rooms_booked` | INT | `rooms_occupied + rooms_canceled` | Same as above. Original demand before cancellations |
| `guests_in_house` | INT | Sum of `guests` of non-cancelled bookings | Summed over time gives guest-nights |
| `arrivals` | INT | Non-cancelled bookings with `arrival_date = d` | Additive |
| `departures` | INT | Non-cancelled bookings with `departure_date = d` | Additive |
| `realized_revenue` | NUMERIC(12,2) | Sum of `adr` of non-cancelled bookings on night d | Additive |
| `lost_revenue` | NUMERIC(12,2) | Sum of `adr` of cancelled bookings that would have stayed on night d (gross, before deposits) | Additive |

- **Nightly ADR** = `SUM(realized_revenue) / NULLIF(SUM(rooms_occupied), 0)`.
- **Occupancy** = `rooms_occupied / capacity` and **RevPAR** = `realized_revenue / capacity`, where `capacity` is a user-entered parameter (computed in the backend, not stored here).
- **Reconciliation (check `12_gold_occupancy_reconciliation`):** total `rooms_occupied` per hotel = total nights (within the range) of non-cancelled bookings in `fact_booking`.

### 5.3 `gold.fact_daily_weather`: periodic snapshot (external source)

- **Purpose:** attach weather context to demand and cancellations ("do rainy nights in the Algarve have fewer guests?",
  a feature for demand forecasting). Used together with `dim_date.is_holiday` / `is_weekend` for day-level analysis.
- **Source:** `silver.weather_daily` (Open-Meteo Historical Weather API, ERA5 reanalysis model) at 2 locations:
  **Lisbon** for City Hotel, **Faro** for Resort Hotel. Joined to `dim_hotel` via `dim_hotel.weather_location`.
- **Grain:** **1 row = 1 hotel × 1 calendar day.** PK `(hotel_key, date_key)`, FKs to `dim_hotel`, `dim_date`.
- **Range:** 2015-01-01 → 2017-12-31 (1,096 days) → **2,192 rows**. Wider than `fact_daily_occupancy` to cover both arrival dates and stay nights.
- **Why a separate fact instead of extra columns in `fact_daily_occupancy`?** (1) the date ranges differ; (2) one source, one table:
  a faulty weather source does not break the main fact; (3) it can join **both** facts without duplicating rows, because its PK is the join key:

| Joins with | Key | Relationship | Meaning |
|---|---|---|---|
| `fact_daily_occupancy` | `hotel_key`, `stay_date_key = date_key` | 1 : 1 | Weather of the stay night (view `kpi_daily_occupancy_weather`) |
| `fact_booking` | `hotel_key`, `arrival_date_key = date_key` | N : 1 | Weather of the arrival date |

| Column | Type | Meaning | Additivity |
|---|---|---|---|
| `hotel_key`, `date_key` | INT PK, FK | | |
| `weather_code` | SMALLINT | WMO weather code of the day | No |
| `weather_group` | TEXT | Group derived from the WMO code: `Clear` (0–1), `Cloudy` (2–3), `Fog` (45, 48), `Drizzle` (51–57), `Rain` (61–67, 80–82), `Snow` (71–77, 85–86), `Thunderstorm` (95–99) | No (used for filtering/grouping) |
| `temp_max_c`, `temp_min_c`, `temp_mean_c` | NUMERIC(4,1) | Temperature at 2 m (°C) | Non-additive: take the `avg` across days |
| `precipitation_mm`, `rain_mm` | NUMERIC(6,1) | Total precipitation (mm) | Additive across time |
| `precipitation_hours` | NUMERIC(4,1) | Hours with precipitation | Additive across time |
| `wind_speed_max_kmh` | NUMERIC(5,1) | Maximum wind speed at 10 m (km/h) | Non-additive (`max`/`avg`) |
| `sunshine_hours` | NUMERIC(5,2) | Sunshine hours | Additive across time |
| `is_rainy_day` | SMALLINT 0/1 | `precipitation_mm >= 1` (the common "rainy day" threshold) | `SUM` = number of rainy days |

- **Not additive across hotels:** the two hotels are at two different locations; summing the precipitation of 2 locations is meaningless.
- **ML:** usable for **demand forecasting** (as multi-year weekly averages, or as a weather forecast in a real deployment).
  The actual weather on the arrival date is **not** used as a **cancellation prediction** feature: at booking time (average lead time ~100 days) nobody knows it yet.
- **Results of the real run (2015–2017):** Lisbon average temperature 16.8 °C, ~453 mm/year; Faro 18.5 °C, ~398 mm/year. Rainy nights within the occupancy
  range: City 148/793, Resort 115/793. Rainy nights at the Resort average 134 occupied rooms versus 153 on dry nights (City: 164 versus 170).

---

## 6. KPI tables for the dashboard (`5x`, as VIEWs)

Views are recomputed from the facts on every query: they always match the facts and need no reloading. The data is small, so no materialized views are needed.
Every non-additive measure is computed from totals (rule 8).

| File | View | Grain | Used by page |
|---|---|---|---|
| `50_kpi_monthly_hotel.sql` | `gold.kpi_monthly_hotel` | hotel × arrival month | KPI overview (drill Year → Quarter → Month) |
| `51_kpi_channel.sql` | `gold.kpi_channel` | hotel × `channel_group` × month | Sales & Marketing (G5) |
| `52_kpi_country.sql` | `gold.kpi_country` | hotel × country × year | Sales & Marketing (G5) |
| `53_kpi_cancellation_profile.sql` | `gold.kpi_cancellation_profile` | hotel × lead time band × `deposit_type` × `channel_group` | Cancellations page |
| `54_kpi_weekly_occupancy.sql` | `gold.kpi_weekly_occupancy` | hotel × ISO week (from `fact_daily_occupancy`) | Demand forecasting, What-if |
| `55_kpi_daily_occupancy_weather.sql` | `gold.kpi_daily_occupancy_weather` | hotel × night (`fact_daily_occupancy` JOIN 1:1 `fact_daily_weather` + holiday/weekend flags from `dim_date`) | Weather/holiday analysis, forecasting features |

Common columns of views `50`–`53`: `bookings`, `canceled_bookings`, `cancellation_rate = canceled / bookings`, `room_nights_sold`,
`realized_revenue`, `lost_revenue`, `adr = realized_revenue / NULLIF(room_nights_sold, 0)`, `avg_lead_time`, `avg_los = room_nights_sold / NULLIF(bookings - canceled, 0)`.
Lead time bands of view `53`: `0–7`, `8–30`, `31–90`, `91–180`, `181–365`, `>365` days.

---

## 7. ML result tables (`ml_*`): contract with `ml/`

These tables are **created and written** by the code in `ml/`, not in `database/gold/`. They are designed here so that the backend and ML agree on the columns from the start.

| Table | Grain | Columns |
|---|---|---|
| `gold.ml_booking_risk` | 1 booking × 1 model version | `booking_id` (→ `fact_booking`), `model_version`, `cancel_probability` NUMERIC(5,4), `risk_band` (`Low`/`Medium`/`High`), `is_test_set` BOOLEAN, `scored_at` |
| `gold.ml_demand_forecast` | 1 hotel × 1 week × 1 version | `hotel_key`, `week_start_date` (→ `dim_date.week_start_date`), `model_version`, `predicted_room_nights`, `lower_bound`, `upper_bound`, `actual_room_nights` (NULL for the future), `horizon_weeks` (weeks from the forecast origin; the prediction interval widens with the horizon), `created_at` |
| `gold.ml_model_metrics` | 1 model × 1 metric | `model_version`, `model_name`, `metric_name` (`auc`, `precision`, `recall`, `mape`…), `metric_value`, `trained_at` |

Time-based train/test split (rule 7): train on `arrival_date` < 2017-01-01, test on the year 2017.

---

## 8. Implementation

| Run order | File | Contents |
|---|---|---|
| bronze/silver | `etl/extract/countries.py`, `database/bronze/03_countries.sql`, `database/silver/03_countries.sql` | **New source (Q4):** ISO 3166 code table + UN M49 regions (`lukes/ISO-3166-Countries-with-Regional-Codes`, 249 rows). Silver fills in the region for TWN and ATA (left blank by the UN) |
| silver | `database/silver/01_hotel_bookings.sql` | Adds `departure_date`, `total_guests`, `party_type`; normalizes `CN → CAN`, `TMP → TLS` |
| 0x | `database/gold/00_business_assumptions.sql` | Table of assumed parameters: `non_refund_deposit_rate = 0.20` |
| 1x | `database/gold/10_dim_date.sql` … `16_dim_booking_profile.sql` | 7 dimensions |
| bronze/silver | `etl/extract/weather.py`, `database/bronze/04_weather_daily.sql`, `database/silver/04_weather_daily.sql` | **New source (Q6):** daily Open-Meteo weather, Lisbon + Faro, 2015–2017 (2,192 rows) |
| 3x | `database/gold/30_fact_booking.sql`, `31_fact_daily_occupancy.sql`, `32_fact_daily_weather.sql` | 3 facts, with PKs, FKs and indexes |
| 5x | `database/gold/50_kpi_monthly_hotel.sql` … `55_kpi_daily_occupancy_weather.sql` | 6 KPI views |

Row counts after the run: `dim_date` 2,191, `dim_hotel` 2, `dim_country` 178, `dim_channel` 26, `dim_room_type` 12, `dim_agent` 334,
`dim_booking_profile` 154, `fact_booking` 119,209, `fact_daily_occupancy` 1,586, `fact_daily_weather` 2,192.

**Data quality checks for gold** (`database/checks/`). Foreign key integrity and `dim_date` coverage are guaranteed by FK constraints (the pipeline fails immediately on a violation), so no separate checks are needed.

| File | Severity | Returns violating rows when | Result |
|---|---|---|---|
| `10_gold_fact_booking_row_count.sql` | error | `count(fact_booking)` ≠ `count(silver)` − rows removed by the rules | ✔ 0 |
| `11_gold_revenue_reconciliation.sql` | error | `booked ≠ realized + lost` or `lost ≠ deposit_retained + net_lost` (difference > €0.01) | ✔ 0 |
| `12_gold_occupancy_reconciliation.sql` | error | Total room-nights by night ≠ total nights of non-cancelled bookings within the range | ✔ 0 |
| `13_gold_adr_outlier.sql` | warning | `adr > 1000` | ⚠ 1 (ADR €5,400, cancelled) |
| `14_gold_weather_coverage.sql` | error | A night in `fact_daily_occupancy` or an arrival date in `fact_booking` has no weather for that hotel | ✔ 0 |

Checks for the weather source in silver: `05_silver_weather_daily_coverage.sql` (error: every location has all days, no gaps; duplicate dates are already blocked by the PK)
and `06_silver_weather_daily_missing_values.sql` (warning: missing temperature/precipitation). Both ✔ 0.

**Changing the default deposit rate:** edit the value in `00_business_assumptions.sql`, then run `python -m etl.run_pipeline --from gold`.
The what-if page lets users try other rates without rerunning the pipeline: the backend computes
`net_lost = lost_revenue − rate × lost_revenue` for `Non Refund` bookings (filtered via `dim_booking_profile.deposit_type`).

---

## 9. Agreed decisions

| # | Question | Team decision | Implemented in |
|---|---|---|---|
| Q1 | 181 anomalous rows (180 without guests, 1 negative ADR): remove them or keep them with a flag? | **Remove them from the fact entirely** | `WHERE` in `gold/30_fact_booking.sql`, check `10_gold_fact_booking_row_count` |
| Q2 | Which country is the code `CN` (1,279 bookings)? | **Canada: changed to `CAN`** (plus `TMP` → `TLS`) | `silver/01_hotel_bookings.sql` |
| Q3 | Does a cancelled `Non Refund` booking count as lost revenue? | **By default the hotel keeps 20% of the deposit.** Both the gross loss (`lost_revenue`) and the net loss (`net_lost_revenue`) are kept; the what-if allows changing the rate | `gold/00_business_assumptions.sql`, columns `deposit_retained`, `net_lost_revenue` |
| Q4 | Add an ISO 3166 country code source? | **Agreed** | `etl/extract/countries.py`, `bronze/03`, `silver/03` |
| Q5 | Separate accumulating snapshot table? | **No**: `fact_booking` already has all 4 date milestones | |
| Q6 | How to integrate weather without duplicating fact rows? (issue #8) | **A separate fact `fact_daily_weather`** with hotel × day grain, joined via conformed dims; Lisbon for City, Faro for Resort. Holidays stay in `dim_date` | `etl/extract/weather.py`, `bronze/04`, `silver/04`, `gold/32`, `gold/55`, checks `05`, `06`, `14` |
