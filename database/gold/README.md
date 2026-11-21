# gold/ — Star schema & bảng phục vụ ứng dụng

Thiết kế chi tiết (đã chốt): [`docs/STAR_SCHEMA.md`](../../docs/STAR_SCHEMA.md). Mô tả cột: `docs/DATA_DICTIONARY.md` mục 5.

| File                              | Bảng                         | Loại                                   |
|-----------------------------------|------------------------------|----------------------------------------|
| `00_business_assumptions.sql`     | `gold.business_assumptions`  | Tham số giả định (tỉ lệ cọc 20%)       |
| `10_dim_date.sql`                 | `gold.dim_date`              | Dimension (role-playing, conformed)    |
| `11_dim_hotel.sql`                | `gold.dim_hotel`             | Dimension (conformed)                  |
| `12_dim_country.sql`              | `gold.dim_country`           | Dimension (cần nguồn mã ISO 3166)      |
| `13_dim_channel.sql`              | `gold.dim_channel`           | Dimension                              |
| `14_dim_room_type.sql`            | `gold.dim_room_type`         | Dimension (role-playing)               |
| `15_dim_agent.sql`                | `gold.dim_agent`             | Dimension (SCD2-ready)                 |
| `16_dim_booking_profile.sql`      | `gold.dim_booking_profile`   | Junk dimension                         |
| `30_fact_booking.sql`             | `gold.fact_booking`          | Transaction fact                       |
| `31_fact_daily_occupancy.sql`     | `gold.fact_daily_occupancy`  | Periodic snapshot fact                 |
| `50_kpi_*.sql` … `54_kpi_*.sql`   | `gold.kpi_*`                 | View tổng hợp cho dashboard            |

Bảng kết quả ML (`gold.ml_*`) do code trong `ml/` ghi vào, **không** tạo ở đây (cột đã thống nhất trong `STAR_SCHEMA.md` mục 7).

Quy ước đánh số: `0x` = tham số, `1x` = dimension, `3x` = fact, `5x` = KPI/view. Dimension phải chạy trước fact.
Mỗi file bắt đầu bằng `DROP TABLE IF EXISTS gold.<bảng> CASCADE;` (CASCADE xóa FK/view phụ thuộc, các file sau sẽ tạo lại).
