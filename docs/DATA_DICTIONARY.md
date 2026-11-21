# Từ điển dữ liệu (Data Dictionary)

> **Quy tắc:** thêm hoặc sửa bảng nào thì cập nhật file này trong **cùng PR**.

## 1. Nguồn: `hotel_bookings.csv` → `bronze.hotel_bookings`

Nguồn: Antonio, Almeida & Nunes (2019), *Hotel booking demand datasets*, Data in Brief 22, 41–49.
Grain: **1 dòng = 1 booking**. 119.390 dòng, 32 cột. Ở bronze, mọi cột là `TEXT`.

| Cột | Ý nghĩa | Giá trị / ghi chú |
|---|---|---|
| `hotel` | Khách sạn | `City Hotel`, `Resort Hotel` |
| `is_canceled` | Booking có bị hủy không | `1` = hủy, `0` = không |
| `lead_time` | Số ngày từ lúc đặt đến ngày đến | |
| `arrival_date_year` / `_month` / `_week_number` / `_day_of_month` | Ngày đến | Tháng ghi bằng chữ tiếng Anh (`July`) |
| `stays_in_weekend_nights` | Số đêm cuối tuần (T7, CN) ở hoặc đã đặt | |
| `stays_in_week_nights` | Số đêm trong tuần (T2–T6) | |
| `adults`, `children`, `babies` | Số người lớn / trẻ em / em bé | `children` có giá trị `NA` |
| `meal` | Gói ăn | `BB` bed & breakfast, `HB` half board, `FB` full board, `SC`/`Undefined` không ăn |
| `country` | Quốc gia của khách | Mã ISO 3166-1 alpha-3; có giá trị `NULL` |
| `market_segment` | Phân khúc thị trường | `TA` = travel agents, `TO` = tour operators, `Direct`, `Corporate`, `Groups`… |
| `distribution_channel` | Kênh phân phối | `TA/TO`, `Direct`, `Corporate`, `GDS` |
| `is_repeated_guest` | Khách quay lại | `1` / `0` |
| `previous_cancellations` | Số lần hủy trước đó của khách | |
| `previous_bookings_not_canceled` | Số booking trước đó không hủy | |
| `reserved_room_type` | Loại phòng đặt | Mã đã ẩn danh (A, B, C…) |
| `assigned_room_type` | Loại phòng được xếp thực tế | ⚠ Có thể chứa thông tin sau khi đặt (rủi ro leakage) |
| `booking_changes` | Số lần sửa booking đến lúc check-in/hủy | ⚠ Rủi ro leakage |
| `deposit_type` | Loại đặt cọc | `No Deposit`, `Non Refund`, `Refundable` |
| `agent` | Mã đại lý | Có `NULL` |
| `company` | Mã công ty đặt/thanh toán | Phần lớn `NULL` |
| `days_in_waiting_list` | Số ngày trong danh sách chờ trước khi được xác nhận | |
| `customer_type` | Loại khách | `Transient`, `Transient-Party`, `Contract`, `Group` |
| `adr` | Average Daily Rate = tổng tiền lưu trú / số đêm | EUR |
| `required_car_parking_spaces` | Số chỗ đỗ xe yêu cầu | |
| `total_of_special_requests` | Số yêu cầu đặc biệt | |
| `reservation_status` | Trạng thái cuối | `Canceled`, `Check-Out`, `No-Show`. ⛔ **Leakage**: không dùng làm feature |
| `reservation_status_date` | Ngày của trạng thái cuối | ⛔ **Leakage** |

Cột kỹ thuật thêm ở bronze: `_source_row` (số dòng trong file), `_source_file`, `_loaded_at`.

## 2. `silver.hotel_bookings`

Grain: **1 dòng = 1 booking**. Khóa chính: `booking_id`.

| Cột | Kiểu | Lấy từ / cách tính |
|---|---|---|
| `booking_id` | BIGINT | `_source_row` (dataset gốc không có ID) |
| `hotel_name` | TEXT | `hotel` |
| `is_canceled` | BOOLEAN | `is_canceled = '1'` |
| `lead_time` | INT | |
| `arrival_date` | DATE | ghép year + month + day_of_month |
| `booking_date` | DATE | `arrival_date - lead_time` |
| `arrival_week_number` | INT | |
| `weekend_nights`, `week_nights` | INT | |
| `total_nights` | INT | `weekend_nights + week_nights` |
| `departure_date` | DATE | `arrival_date + total_nights` |
| `adults`, `children`, `babies` | INT | `children`: `NA` → 0 |
| `total_guests` | INT | `adults + children + babies` |
| `party_type` | TEXT | `Other` (0 người lớn) / `Family` (có trẻ em, em bé) / `Solo` (1 người lớn) / `Couple` (2) / `Group` (≥ 3) |
| `meal` | TEXT | `Undefined` → `SC` |
| `country_code` | TEXT | `NULL`/`NA` → NULL; `CN` → `CAN` (Canada), `TMP` → `TLS` (Đông Timor) |
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

**Vấn đề chất lượng đã phát hiện** (`database/checks/`, chưa lọc ở silver):

| Check | Số dòng | Xử lý ở gold (đã chốt) |
|---|---|---|
| Không có khách (0 người lớn, 0 trẻ em, 0 em bé) | 180 | Loại khỏi `fact_booking` |
| ADR âm | 1 | Loại khỏi `fact_booking` |
| 0 đêm lưu trú | 715 | Giữ; ADR tính từ tổng nên không bị ảnh hưởng |
| `country_code` NULL | 488 | Gán `country_key = -1` (Unknown) trong `dim_country` |

## 3. `bronze.pt_holidays` → `silver.pt_holidays`

Grain: **1 dòng = 1 ngày lễ** (gộp tên nếu trùng ngày). Năm 2013–2018. Sinh bằng thư viện `holidays` (mã quốc gia `PT`).

| Cột | Kiểu (silver) | Ý nghĩa |
|---|---|---|
| `holiday_date` | DATE (PK) | Ngày lễ |
| `holiday_name` | TEXT | Tên ngày lễ (tiếng Bồ Đào Nha) |

## 4. `bronze.countries` → `silver.countries`

Nguồn: [lukes/ISO-3166-Countries-with-Regional-Codes](https://github.com/lukes/ISO-3166-Countries-with-Regional-Codes) (`all/all.csv`, CC BY-SA 4.0).
Grain: **1 dòng = 1 quốc gia/vùng lãnh thổ** (249 dòng). Bronze giữ nguyên tên cột CSV (có dấu gạch ngang).

| Cột (silver) | Kiểu | Lấy từ |
|---|---|---|
| `country_code` | TEXT (PK) | `alpha-3` |
| `country_code_alpha2` | TEXT | `alpha-2` |
| `country_name` | TEXT | `name` |
| `region` | TEXT | `region` (châu lục UN M49); bổ sung TWN → Asia, ATA → Antarctica |
| `sub_region` | TEXT | `sub-region` |

## 5. Gold

Thiết kế đầy đủ (lý do, công thức, ERD): [`STAR_SCHEMA.md`](STAR_SCHEMA.md). Quy ước: `-1` = Unknown, `0` = không áp dụng; FK trong fact không bao giờ NULL.

### `gold.business_assumptions`: tham số giả định (1 dòng = 1 tham số)
| Cột | Ý nghĩa |
|---|---|
| `param_name` (PK) | Tên tham số. Hiện có `non_refund_deposit_rate` = 0.20 |
| `param_value`, `unit`, `description` | Giá trị, đơn vị, mô tả |

### Dimension

| Bảng | Grain (số dòng) | Cột |
|---|---|---|
| `dim_date` | 1 ngày, 2013–2018 (2.191) | `date_key` (PK, YYYYMMDD), `full_date`, `day_of_month`, `day_of_week` (ISO 1–7), `day_name`, `is_weekend`, `iso_week`, `iso_year`, `week_start_date`, `month`, `month_name`, `quarter`, `year`, `year_month`, `season` (High/Shoulder/Low), `is_holiday`, `holiday_name` |
| `dim_hotel` | 1 khách sạn (2) | `hotel_key` (PK), `hotel_name`, `hotel_type`, `city`, `country_code`, `latitude`, `longitude` |
| `dim_country` | 1 mã quốc gia + Unknown (178) | `country_key` (PK, -1 = Unknown), `country_code`, `country_name`, `region`, `sub_region`, `is_domestic`, `market_group` (Domestic / Core Europe / Other Europe / Rest of World / Unknown) |
| `dim_channel` | 1 tổ hợp segment × channel (26) | `channel_key` (PK), `market_segment`, `distribution_channel`, `channel_group` (OTA / Offline TA/TO / Direct / Corporate / Groups / Other), `is_intermediated` |
| `dim_room_type` | 1 mã phòng (12) | `room_type_key` (PK), `room_type_code`, `room_type_label` |
| `dim_agent` | 1 đại lý + "No agent" (334) | `agent_key` (PK, 0 = không qua đại lý), `agent_id`, `agent_label`, `has_agent`, `valid_from`, `valid_to`, `is_current` |
| `dim_booking_profile` | 1 tổ hợp junk (154) | `booking_profile_key` (PK), `meal`, `meal_name`, `deposit_type`, `customer_type`, `is_repeated_guest`, `party_type` |

### `gold.fact_booking`: 1 dòng = 1 booking (119.209 dòng)

| Nhóm | Cột |
|---|---|
| Khóa | `booking_id` (PK, degenerate), `hotel_key`, `booking_date_key`, `arrival_date_key`, `departure_date_key`, `status_date_key` ⛔, `country_key`, `channel_key`, `agent_key`, `reserved_room_type_key`, `assigned_room_type_key` ⚠, `booking_profile_key` |
| Degenerate | `company_id`, `reservation_status` ⛔ |
| Đếm | `booking_count` (=1), `is_canceled` (0/1), `lead_time`, `weekend_nights`, `week_nights`, `total_nights`, `room_nights_sold` ⛔, `adults`, `children`, `babies`, `guests` |
| Tiền (EUR) | `adr` (non-additive), `booked_revenue` = adr × total_nights, `realized_revenue` ⛔ (không hủy), `lost_revenue` ⛔ (hủy, gộp), `deposit_retained` ⛔ (hủy + Non Refund × tỉ lệ cọc), `net_lost_revenue` ⛔ = lost − deposit |
| Hành vi | `days_in_waiting_list`, `previous_cancellations`, `previous_bookings_not_canceled`, `total_of_special_requests`, `required_car_parking_spaces`, `booking_changes` ⚠, `is_room_changed` ⚠, `cancel_lead_days` ⛔ |

⛔ = suy ra từ kết quả hủy, cấm dùng làm feature ML. ⚠ = cân nhắc (chỉ biết sau khi đặt).

### `gold.fact_daily_occupancy`: 1 dòng = 1 khách sạn × 1 đêm (1.586 dòng, 2015-07-01 → 2017-08-31)

| Cột | Ý nghĩa |
|---|---|
| `hotel_key`, `stay_date_key` | PK, FK |
| `rooms_occupied` | Số booking không hủy có đêm này |
| `rooms_canceled` | Số booking đã hủy lẽ ra có đêm này |
| `rooms_booked` | `rooms_occupied + rooms_canceled` |
| `guests_in_house` | Số khách lưu trú đêm này |
| `arrivals`, `departures` | Lượt đến / trả phòng (booking không hủy) |
| `realized_revenue`, `lost_revenue` | Tổng `adr` của booking không hủy / đã hủy ở đêm này |

### View KPI

| View | Grain | Cột riêng (ngoài bộ cột chung) |
|---|---|---|
| `kpi_monthly_hotel` | khách sạn × tháng đến | `year`, `quarter`, `month`, `year_month` |
| `kpi_channel` | khách sạn × `channel_group` × tháng đến | `channel_group`, `year`, `month`, `year_month` |
| `kpi_country` | khách sạn × quốc gia × năm đến | `country_code`, `country_name`, `region`, `market_group`, `year` |
| `kpi_cancellation_profile` | khách sạn × nhóm lead time × `deposit_type` × `channel_group` | `lead_time_band`, `lead_time_band_order`, `deposit_type`, `channel_group` |
| `kpi_weekly_occupancy` | khách sạn × tuần ISO | `iso_year`, `iso_week`, `week_start_date`, `days_in_week`, `is_complete_week`, `room_nights_sold`, `room_nights_canceled`, `room_nights_booked`, `guest_nights`, `arrivals`, `realized_revenue`, `lost_revenue`, `adr`, `night_cancellation_rate` |

Bộ cột chung của 4 view đầu: `bookings`, `canceled_bookings`, `cancellation_rate`, `room_nights_sold`, `realized_revenue`,
`lost_revenue`, `net_lost_revenue`, `adr`, `avg_lead_time`, `avg_los`. Tỉ lệ và ADR đều tính lại từ tổng.

### `gold.ml_demand_forecast`: 1 dòng = 1 khách sạn × 1 tuần × 1 phiên bản model (252 dòng)

Ghi bởi `python -m ml.forecast.train` (DDL: `database/ml/03_ml_demand_forecast.sql`), không do pipeline ETL tạo.
Chi tiết phương pháp: [`ml/README.md`](../ml/README.md#e4-dự-báo-nhu-cầu-theo-tuần).

| Cột | Ý nghĩa |
|---|---|
| `hotel_key`, `week_start_date`, `model_version` | PK. `week_start_date` = Thứ Hai đầu tuần (khớp `dim_date.week_start_date`) |
| `model_version` | `forecast_gbm_v1` (model chính), `forecast_seasonal_naive_v1`, `forecast_moving_avg_v1` (baseline). Khớp `ml_model_metrics.model_version` |
| `predicted_room_nights` | Room-nights bán được (booking không hủy) dự báo cho tuần đó |
| `lower_bound`, `upper_bound` | Khoảng dự báo 80% (từ phân phối sai số backtest theo horizon) |
| `actual_room_nights` | Thực tế; NULL với tuần tương lai và tuần 2017-08-28 (chỉ có 4/7 đêm dữ liệu) |
| `horizon_weeks` | Dự báo trước bao nhiêu tuần: 1 cho các tuần backtest 2017, 1..8 cho 8 tuần tương lai |
| `created_at` | Thời điểm ghi |

Mỗi model có 84 dòng: 2 khách sạn × (34 tuần backtest 2017-01-02 → 2017-08-21 + 8 tuần tương lai 2017-08-28 → 2017-10-16).
Metric tương ứng nằm trong `gold.ml_model_metrics` với `model_name` bắt đầu bằng `forecast_`
(`mape`, `mape_h1`…`mape_h8`, `mape_<hotel>`, `mape_h1_<hotel>`, `interval_coverage_80`; `dataset` = `backtest` hoặc
`calibration`). MAPE lưu dạng tỉ lệ (0.0857 = 8,57%).

## 6. `meta.etl_run_log`

| Cột | Ý nghĩa |
|---|---|
| `log_id` | Khóa tự tăng |
| `run_id` | UUID của một lần chạy pipeline |
| `step` | Tên bước, ví dụ `silver/01_hotel_bookings.sql` |
| `status` | `running`, `success`, `warning`, `failed` |
| `rows_affected` | Số dòng nạp, hoặc số dòng vi phạm (với check) |
| `message` | Thông báo lỗi hoặc cảnh báo |
| `started_at`, `finished_at` | Thời gian |
