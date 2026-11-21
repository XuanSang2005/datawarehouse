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
| `adults`, `children`, `babies` | INT | `children`: `NA` → 0 |
| `meal` | TEXT | `Undefined` → `SC` |
| `country_code` | TEXT | `NULL`/`NA` → NULL |
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

| Check | Số dòng | Hướng xử lý ở gold (cần chốt) |
|---|---|---|
| Không có khách (0 người lớn, 0 trẻ em, 0 em bé) | 180 | Loại bỏ |
| ADR âm | 1 | Loại bỏ |
| 0 đêm lưu trú | 715 | Giữ, nhưng không tính vào ADR |
| `country_code` NULL | 488 | Gán thành viên "Unknown" trong `dim_country` |

## 3. `bronze.pt_holidays` → `silver.pt_holidays`

Grain: **1 dòng = 1 ngày lễ** (gộp tên nếu trùng ngày). Năm 2013–2018. Sinh bằng thư viện `holidays` (mã quốc gia `PT`).

| Cột | Kiểu (silver) | Ý nghĩa |
|---|---|---|
| `holiday_date` | DATE (PK) | Ngày lễ |
| `holiday_name` | TEXT | Tên ngày lễ (tiếng Anh) |

## 4. Gold

_Chưa có bảng nào được tạo._ Thiết kế đề xuất, có đủ từng cột, nằm ở [`STAR_SCHEMA.md`](STAR_SCHEMA.md).
Khi file SQL của bảng nào được merge thì chép mô tả cột của bảng đó vào đây.

## 5. `meta.etl_run_log`

| Cột | Ý nghĩa |
|---|---|
| `log_id` | Khóa tự tăng |
| `run_id` | UUID của một lần chạy pipeline |
| `step` | Tên bước, ví dụ `silver/01_hotel_bookings.sql` |
| `status` | `running`, `success`, `warning`, `failed` |
| `rows_affected` | Số dòng nạp, hoặc số dòng vi phạm (với check) |
| `message` | Thông báo lỗi hoặc cảnh báo |
| `started_at`, `finished_at` | Thời gian |
