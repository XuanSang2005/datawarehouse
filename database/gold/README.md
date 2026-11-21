# gold/ — Star schema & application-serving tables

Detailed design (agreed): [`docs/STAR_SCHEMA.md`](../../docs/STAR_SCHEMA.md). Column descriptions: `docs/DATA_DICTIONARY.md` section 6.

| File                              | Table                        | Type                                   |
|-----------------------------------|------------------------------|----------------------------------------|
| `00_business_assumptions.sql`     | `gold.business_assumptions`  | Assumption parameters (20% deposit rate) |
| `10_dim_date.sql`                 | `gold.dim_date`              | Dimension (role-playing, conformed)    |
| `11_dim_hotel.sql`                | `gold.dim_hotel`             | Dimension (conformed)                  |
| `12_dim_country.sql`              | `gold.dim_country`           | Dimension (needs the ISO 3166 code source) |
| `13_dim_channel.sql`              | `gold.dim_channel`           | Dimension                              |
| `14_dim_room_type.sql`            | `gold.dim_room_type`         | Dimension (role-playing)               |
| `15_dim_agent.sql`                | `gold.dim_agent`             | Dimension (SCD2-ready)                 |
| `16_dim_booking_profile.sql`      | `gold.dim_booking_profile`   | Junk dimension                         |
| `30_fact_booking.sql`             | `gold.fact_booking`          | Transaction fact                       |
| `31_fact_daily_occupancy.sql`     | `gold.fact_daily_occupancy`  | Periodic snapshot fact                 |
| `32_fact_daily_weather.sql`       | `gold.fact_daily_weather`    | Periodic snapshot fact (weather, needs the Open-Meteo source) |
| `50_kpi_*.sql` … `55_kpi_*.sql`   | `gold.kpi_*`                 | Aggregate views for the dashboard      |

ML result tables (`gold.ml_*`) are written by the code in `ml/` and are **not** created here (columns agreed in `STAR_SCHEMA.md` section 7).

Numbering convention: `0x` = parameters, `1x` = dimensions, `3x` = facts, `5x` = KPIs/views. Dimensions must run before facts.
Each file starts with `DROP TABLE IF EXISTS gold.<table> CASCADE;` (CASCADE drops dependent FKs/views; later files recreate them).
