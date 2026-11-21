# gold/ — Star schema & bảng phục vụ ứng dụng

Chưa có file SQL: phần này làm **sau khi nhóm chốt thiết kế star schema**.

Các bảng dự kiến (xem `docs/ARCHITECTURE.md` mục 4):

| File (dự kiến)            | Bảng                       | Loại                          |
|---------------------------|----------------------------|-------------------------------|
| `10_dim_date.sql`         | `gold.dim_date`            | Dimension (role-playing)      |
| `11_dim_hotel.sql`        | `gold.dim_hotel`           | Dimension                     |
| `12_dim_country.sql`      | `gold.dim_country`         | Dimension                     |
| `13_dim_channel.sql`      | `gold.dim_channel`         | Dimension                     |
| `14_dim_room_type.sql`    | `gold.dim_room_type`       | Dimension                     |
| `15_dim_agent.sql`        | `gold.dim_agent`           | Dimension                     |
| `16_dim_booking_profile.sql` | `gold.dim_booking_profile` | Junk dimension             |
| `30_fact_booking.sql`     | `gold.fact_booking`        | Transaction fact              |
| `31_fact_daily_occupancy.sql` | `gold.fact_daily_occupancy` | Periodic snapshot fact   |
| `50_kpi_*.sql`            | `gold.kpi_*`               | Bảng/view tổng hợp cho dashboard |

Bảng kết quả ML (`gold.ml_*`) do code trong `ml/` ghi vào, **không** tạo ở đây.

Quy ước đánh số: `1x` = dimension, `3x` = fact, `5x` = KPI/view. Dimension phải chạy trước fact.
