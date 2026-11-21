# Kiến trúc hệ thống

## 1. Tổng quan

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   NGUỒN DỮ LIỆU                                         │
│   hotel_bookings.csv  pt_holidays (holidays)  countries (ISO 3166)  weather (dự kiến)   │
└───────────────┬─────────────────────────────────────────────────────────────────────────┘
                │  etl/extract/*.py  ->  data/raw/
                ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          POSTGRESQL (lakehouse, kiến trúc Medallion)                     │
│                                                                                          │
│   ┌──────────┐  etl/load  ┌──────────┐  database/  ┌──────────┐  database/  ┌──────────┐ │
│   │ data/raw │ ─────────▶ │  BRONZE  │ ──silver──▶ │  SILVER  │ ───gold───▶ │   GOLD   │ │
│   │  (file)  │   COPY     │ thô, TEXT│   *.sql     │ sạch,kiểu│   *.sql     │ star     │ │
│   └──────────┘            └──────────┘             └──────────┘             │ schema   │ │
│                                                         │                   │ + KPI    │ │
│   ┌──────────┐                                          │ ml/ (train)       │ + ml_*   │ │
│   │   META   │  log mỗi bước pipeline                    └──────────────────▶│          │ │
│   └──────────┘                                                              └────┬─────┘ │
└──────────────────────────────────────────────────────────────────────────────────┼───────┘
                                                                                   │ SELECT
                                                         ┌─────────────────────────▼──────┐
                                                         │ BACKEND: FastAPI (:8000)       │
                                                         │ routes → services → repos      │
                                                         └─────────────────────────┬──────┘
                                                                                   │ JSON /api/*
                                                         ┌─────────────────────────▼──────┐
                                                         │ FRONTEND: React + Vite (:5173) │
                                                         │ Dashboard, what-if, dự báo     │
                                                         └────────────────────────────────┘
                                                                  ▲
                                                       Người ra quyết định
```

## 2. Thành phần và trách nhiệm

| Thành phần | Thư mục | Làm gì | KHÔNG làm gì |
|---|---|---|---|
| **Database** | `database/` | Định nghĩa schema, bảng; biến đổi bằng SQL; kiểm tra chất lượng | — |
| **ETL** | `etl/` | Tải nguồn, nạp bronze, chạy SQL theo thứ tự, ghi log | Không biến đổi dữ liệu bằng pandas |
| **ML** | `ml/` | Khám phá dữ liệu, train mô hình, ghi kết quả vào `gold.ml_*` | Không phục vụ request web |
| **Backend** | `backend/` | Đọc `gold`/`meta`, tính toán what-if, trả JSON | Không đọc bronze/silver, không train |
| **Frontend** | `frontend/` | Hiển thị, tương tác (lọc, drill-down, thanh trượt) | Không tự tính KPI phức tạp |

## 3. Luồng dữ liệu: kiến trúc Medallion

| Layer | Schema | Quy tắc | Ví dụ |
|---|---|---|---|
| **Raw files** | `data/raw/` | File tải về, không sửa tay | `hotel_bookings.csv` |
| **Bronze** | `bronze` | Giữ nguyên 100% nguồn, mọi cột `TEXT`, thêm `_source_row`, `_source_file`, `_loaded_at` | `bronze.hotel_bookings` |
| **Silver** | `silver` | Ép kiểu, chuẩn hóa NULL, tạo cột dẫn xuất đơn giản, **không lọc dòng** | `silver.hotel_bookings` (`arrival_date`, `booking_date`, `total_nights`) |
| **Gold** | `gold` | Star schema, surrogate key, quyết định lọc dữ liệu bất thường, bảng KPI | `gold.fact_booking`, `gold.dim_date` |
| **Meta** | `meta` | Log vận hành pipeline | `meta.etl_run_log` |

**Chiến lược nạp:** *full load*. Mỗi lần chạy sẽ tạo lại bảng, vì dataset là tĩnh.
Nếu triển khai thật với dữ liệu mới hằng ngày thì chuyển sang *incremental load* theo `reservation_status_date`,
và dùng SCD Type 2 cho các dimension thay đổi (ví dụ agent).

**Các bước pipeline** (`etl/run_pipeline.py`):
```
init → extract → bronze → silver → gold → checks
```
Mỗi bước, và mỗi file SQL, được ghi một dòng vào `meta.etl_run_log` (trạng thái, số dòng, lỗi).

## 4. Mô hình dữ liệu Gold: star schema

> Thiết kế chi tiết (từng cột, grain, công thức measure, quyết định đã chốt): [`STAR_SCHEMA.md`](STAR_SCHEMA.md). SQL: `database/gold/`.

```
                         ┌──────────────┐
                         │  dim_date    │ (role-playing: booking / arrival / departure / status)
                         └──────┬───────┘
     ┌──────────────┐           │           ┌──────────────┐
     │ dim_country  ├───┐       │       ┌───┤  dim_hotel   │ (conformed)
     └──────────────┘   │ ┌─────▼─────┐ │   └──────────────┘
     ┌──────────────┐   ├─┤fact_booking├─┤   ┌──────────────┐
     │ dim_channel  ├───┤ └─────┬─────┘ ├───┤dim_room_type │ (reserved / assigned)
     └──────────────┘   │       │       │   └──────────────┘
     ┌──────────────┐   │       │       │   ┌──────────────┐
     │dim_booking_  ├───┘       │       └───┤  dim_agent   │ (SCD2-ready)
     │profile (junk)│           │           └──────────────┘
     └──────────────┘   ┌───────▼──────────────┐
                        │ fact_daily_occupancy │ (periodic snapshot: 1 dòng = 1 khách sạn × 1 đêm)
                        └──────────────────────┘
```

- **`fact_booking`**: grain = 1 booking (~119.209 dòng sau khi loại 181 dòng bất thường).
  Measures: `booking_count`, `is_canceled`, `lead_time`, `total_nights`, `room_nights_sold`, `guests`, `adr` (non-additive),
  `booked_revenue`, `realized_revenue`, `lost_revenue`, `deposit_retained`, `net_lost_revenue`, `cancel_lead_days`.
- **`fact_daily_occupancy`**: grain = 1 khách sạn × 1 đêm (1.586 dòng, 2015-07-01 → 2017-08-31).
  Measures: `rooms_occupied`, `rooms_canceled`, `rooms_booked`, `guests_in_house`, `arrivals`, `departures`, `realized_revenue`, `lost_revenue`. Dùng cho dự báo nhu cầu và what-if overbooking.
- **`kpi_*`** (view): tổng hợp sẵn cho từng trang dashboard.
- **`business_assumptions`**: tham số giả định mà dataset không có (tỉ lệ cọc Non Refund giữ lại, mặc định 20%).
- **`ml_booking_risk`**, **`ml_demand_forecast`**, **`ml_model_metrics`**: do `ml/` ghi.

## 5. Backend: phân tầng

```
HTTP request
   │
   ▼
api/routes/*.py      ← nhận tham số, validate (Pydantic), gọi service. KHÔNG có SQL.
   │
   ▼
services/*.py        ← logic nghiệp vụ: tính what-if, khuyến nghị overbooking, gộp dữ liệu.
   │
   ▼
repositories/*.py    ← CHỈ câu SQL SELECT trên gold/meta, trả list[dict].
   │
   ▼
PostgreSQL
```
- `core/config.py`: đọc `.env`. `core/db.py`: engine SQLAlchemy dùng chung.
- Lỗi DB được bắt tập trung trong `main.py`, trả **HTTP 503** cho FE và log đầy đủ ở terminal backend.
- Lỗi nghiệp vụ (`core/errors.py`) cũng được bắt tập trung: `DataNotReadyError` → **HTTP 404** kèm `hint`
  (vd bảng `gold.ml_*` chưa có → lệnh chạy script ML); `InvalidParameterError` → **HTTP 422**.
- Bộ lọc dùng chung (`hotel_key`, `date_from`, `date_to` theo ngày đến, `channel_group`, `country_code`):
  `api/deps.py` đọc query string, `repositories/booking_sql.py` dựng `WHERE` bằng bind parameter.
- Measure non-additive: repository chỉ trả TỔNG, `services/kpi_math.py` tính tỉ lệ/ADR từ tổng (quy tắc 8).
- What-if (`services/what_if_service.py`): hàm thuần, công thức ghi trong docstring; công suất, chi phí
  đền bù, hoa hồng OTA là tham số người dùng nhập (quy tắc 10). Danh sách endpoint: `backend/README.md`.

## 6. Frontend

```
pages/*.tsx ──dùng──▶ hooks/useApi.ts ──gọi──▶ api/endpoints.ts ──▶ api/client.ts ──fetch /api/*──▶ Vite proxy ──▶ backend
     │
     └──dùng──▶ components/ (layout, common, charts, filters)
```
- `routes.tsx` là danh sách trang duy nhất; Sidebar và Router cùng đọc từ đây.
- Vite proxy `/api` sang `localhost:8000` (dev); nginx proxy sang `backend:8000` (Docker). FE không cần biết URL backend và không gặp lỗi CORS.

## 7. Cấu hình và cổng

| Biến / Cổng | Giá trị mặc định | Dùng bởi |
|---|---|---|
| `.env` (thư mục gốc) | copy từ `.env.example` | ETL, backend, Vite, docker compose |
| PostgreSQL | `localhost:5432`, DB `tourism_dw` | |
| Backend | `localhost:8000` (`/docs` = Swagger) | |
| Frontend | `localhost:5173` | |

## 8. Lý do chọn công nghệ

| Lựa chọn | Lý do | Phương án đã cân nhắc |
|---|---|---|
| **PostgreSQL + Docker** | Phổ biến, SQL chuẩn, cả nhóm chạy giống hệt nhau | DuckDB (khó dùng chung), SQL Server (nặng) |
| **Medallion trên 1 DB (schema riêng)** | Thể hiện rõ lakehouse mà vẫn đơn giản | Lưu Parquet trên object storage (quá mức cần) |
| **Python + SQL thuần** | Dễ debug, đủ cho dataset tĩnh, mỗi file SQL là một bước rõ ràng | dbt, Airflow (tốn thời gian setup) |
| **FastAPI** | Nhanh, tự sinh tài liệu `/docs`, cùng ngôn ngữ Python với ETL/ML | Flask, Django |
| **React + Vite + TS** | Tương tác mạnh (yêu cầu "interactive" của tiêu chí 50% điểm), type an toàn | Streamlit, Power BI |

## 9. Nhật ký quyết định

| Ngày | Quyết định |
|---|---|
| 2026-11-21 | Chọn bài toán quản lý doanh thu và hủy phòng, dataset Hotel Booking Demand |
| 2026-11-21 | Stack: PostgreSQL + Python/SQL + FastAPI + React |
| 2026-11-21 | Bronze lưu TEXT; silver không lọc dòng; quyết định lọc dữ liệu bất thường đặt ở gold |
| 2026-11-21 | Chốt star schema (`STAR_SCHEMA.md`): 7 dimension, 2 fact, 5 view KPI |
| 2026-11-21 | Loại 181 dòng bất thường khỏi fact; `CN` → `CAN`; giả định giữ 20% cọc khi booking Non Refund bị hủy; thêm nguồn mã ISO 3166 |
| 2026-11-21 | Backend E5: API dùng mã `UNK` cho quốc gia không rõ; what-if chỉ nhận thêm đặt phòng ở đêm "kín trên sổ" (đặt ≥ công suất), dùng tỉ lệ hủy thực tế từng đêm |
