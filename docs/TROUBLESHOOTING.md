# Xử lý lỗi: lỗi gì, tìm ở đâu

## Bước 0: Xác định lỗi nằm ở tầng nào

Mở **http://localhost:5173/system** (trang *Trạng thái hệ thống*):

| Trang báo | Lỗi ở tầng | Đi tới |
|---|---|---|
| Trang không mở được | **Frontend** chưa chạy | [§4](#4-frontend) |
| "Không gọi được backend" | **Backend** chưa chạy hoặc sai cổng | [§3](#3-backend) |
| Backend → Database: `down` | **Database** chưa chạy hoặc sai `.env` | [§1](#1-database) |
| Bảng ETL có dòng `failed` | **Pipeline** | [§2](#2-pipeline-etl) |
| Mọi thứ xanh nhưng số liệu sai | **SQL biến đổi** (silver/gold) | [§5](#5-số-liệu-sai) |

```
Lỗi xuất hiện ở đâu?             Nhìn vào đâu?
─────────────────────────────────────────────────────────────────────────
Trình duyệt (F12 → Console)  →  frontend/src/...
Terminal chạy `npm run dev`  →  frontend/ (lỗi build/TypeScript)
Terminal chạy uvicorn        →  backend/app/... (traceback chỉ đúng file)
Terminal chạy run_pipeline   →  etl/ hoặc database/<layer>/<file>.sql
Bảng meta.etl_run_log        →  bước nào lỗi, thông báo lỗi
GitHub Actions (CI) đỏ       →  tab Actions → job nào đỏ → xem log
```

---

## 1. Database

| Triệu chứng | Nguyên nhân | Cách sửa |
|---|---|---|
| `Không kết nối được DB ... Connection refused` | Container DB chưa chạy | `docker compose up -d db`, rồi kiểm tra bằng `docker compose ps` |
| `password authentication failed` | `.env` khác với lúc tạo volume | Sửa `.env` cho đúng, **hoặc** reset: `docker compose down -v && docker compose up -d db` |
| `port is already allocated` / `address already in use` | Máy đã có PostgreSQL khác chiếm cổng 5432 | Đổi `POSTGRES_PORT=5433` trong `.env` |
| `Cannot connect to the Docker daemon` | Docker Desktop chưa mở | Mở Docker Desktop |

Xem log của DB:
```bash
docker compose logs db --tail 50
```
Mở psql:
```bash
docker compose exec db psql -U dwh -d tourism_dw
```

## 2. Pipeline (ETL)

Pipeline in ra **đúng bước và đúng file** bị lỗi, ví dụ:
```
ERROR ✘ Bước 'silver/01_hotel_bookings.sql' lỗi: invalid input syntax for type integer: "NA"
```
Nghĩa là: mở `database/silver/01_hotel_bookings.sql`, tìm cột đang ép `::INT` mà dữ liệu có `"NA"`.

Xem lịch sử các lần chạy:
```sql
SELECT step, status, rows_affected, message, started_at
FROM meta.etl_run_log ORDER BY log_id DESC LIMIT 20;
```

| Tên bước lỗi | File cần mở |
|---|---|
| `init/...` | `database/init/` |
| `extract/<nguon>` | `etl/extract/<nguon>.py` (lỗi mạng: thử lại, hoặc tải file thủ công vào `data/raw/`) |
| `extract/weather_daily` | `etl/extract/weather.py`. Xem bảng Open-Meteo bên dưới |
| `bronze/NN_xxx.sql` | `database/bronze/NN_xxx.sql` (DDL) |
| `bronze/load_<nguon>` | `etl/load/bronze_loader.py`. Thường do **header CSV không khớp DDL** (thông báo liệt kê cột thiếu/thừa) |
| `silver/NN_xxx.sql`, `gold/NN_xxx.sql` | Đúng file SQL đó |
| `checks/NN_xxx.sql` (failed) | Dữ liệu vi phạm điều kiện **error**. Chạy câu SELECT trong file để xem dòng vi phạm |

| Triệu chứng khác | Cách sửa |
|---|---|
| `ModuleNotFoundError: No module named 'etl'` | Phải chạy **từ thư mục gốc repo**: `python -m etl.run_pipeline` |
| `ModuleNotFoundError: psycopg / pandas...` | Chưa activate venv, hoặc chưa `pip install -r requirements-dev.txt` |
| `relation "silver.xxx" does not exist` | Chưa chạy bước trước. Chạy lại toàn bộ: `python -m etl.run_pipeline` |
| Gold chạy sai thứ tự (fact trước dim) | Đổi số trong tên file: dim `1x`, fact `3x` |
| `checks/05_silver_weather_daily_coverage` hoặc `14_gold_weather_coverage` failed | File `data/raw/weather_daily.csv` cũ hoặc thiếu ngày. Tải lại: `python -m etl.run_pipeline --refresh-sources` |

**Nguồn thời tiết Open-Meteo** (`extract/weather_daily`):

| Thông báo | Nguyên nhân | Cách sửa |
|---|---|---|
| `Open-Meteo trả HTTP 429 ..., thử lại sau 2s` (WARNING) | Quá giới hạn request/phút | Không cần làm gì, extract tự thử lại tối đa 4 lần |
| `Open-Meteo trả HTTP 429 ...: Daily API request limit exceeded` | Quá giới hạn ~10.000 request/ngày **theo IP** (mạng trường/công ty, VPN dùng chung IP dễ gặp) | Đổi mạng (ví dụ 4G) rồi chạy lại, hoặc xin file `weather_daily.csv` của bạn cùng nhóm bỏ vào `data/raw/`. Pipeline thấy file có sẵn sẽ không gọi API nữa |
| `WeatherDataError: Ngày trả về không khớp ...` | API trả thiếu/trùng ngày (hiếm) | Chạy lại `--refresh-sources`. File lỗi không được ghi vào `data/raw/` |

**Debug một file SQL riêng lẻ:** copy nội dung file vào psql, DBeaver hoặc VS Code SQLTools rồi chạy từng đoạn.

## 2b. Docker demo (`docker compose --profile app up -d --build`)

Kiểm tra demo từ đầu (nên làm trước buổi bảo vệ):
```bash
docker compose --profile app down -v
```
```bash
docker compose --profile app up -d --build
```
```bash
docker compose logs -f etl
```
Đợi `✔ Pipeline hoàn tất`, rồi mở http://localhost:5173/system.

| Triệu chứng | Nguyên nhân | Cách sửa |
|---|---|---|
| Trang chạy nhưng không có số liệu, `relation "gold.xxx" does not exist` | Container `etl` chưa chạy xong hoặc bị lỗi | `docker compose ps -a` xem `etl` có `Exited (0)` không; `docker compose logs etl` để xem bước lỗi, rồi tra bảng §2 |
| `etl` báo `Không kết nối được DB` | `db` chưa healthy, hoặc `.env` khác lúc tạo volume | `docker compose logs db`; reset: `docker compose --profile app down -v` |
| Sửa SQL/ETL nhưng Docker vẫn chạy code cũ | Image chưa build lại | Thêm `--build`, hoặc `docker compose build etl` |
| Muốn tải lại file nguồn trong Docker | File nằm trong volume `rawdata` | `docker compose run --rm etl python -m etl.run_pipeline --refresh-sources` |
| Build lỗi `CERTIFICATE_VERIFY_FAILED` khi `pip install` / `npm ci` | Mạng có proxy chặn SSL (mạng công ty) | Build ở mạng khác. Đây không phải lỗi của repo |

**Vấn đề đã phát hiện khi kiểm tra demo (issue #8):** trước đây `--profile app` chỉ bật db + backend + frontend,
nên từ DB rỗng ứng dụng chạy nhưng **không có dữ liệu** (phải tự chạy pipeline bằng venv). Đã thêm service `etl`.

## 3. Backend

Traceback trong terminal uvicorn luôn chỉ ra **file và dòng** gây lỗi. Đọc từ dưới lên.

| Mã lỗi HTTP | Ý nghĩa | Tìm ở |
|---|---|---|
| **404** | Sai đường dẫn, hoặc chưa include router | `app/api/router.py` |
| **422** | Tham số request sai kiểu hoặc sai giới hạn | Khai báo tham số trong `app/api/routes/*.py`, hoặc `app/schemas/` |
| **500** | Lỗi code Python | Traceback → thường ở `app/services/` |
| **503** `Database error` | Lỗi SQL hoặc mất kết nối DB | `app/repositories/*.py`; xem log `Lỗi database tại ...` |
| `ResponseValidationError` | Dữ liệu trả về không khớp schema | So sánh repository với `app/schemas/` |

| Triệu chứng | Cách sửa |
|---|---|
| `ModuleNotFoundError: No module named 'app'` | Chạy uvicorn **từ trong thư mục `backend/`** |
| `relation "gold.xxx" does not exist` | Chưa chạy pipeline, hoặc chưa có file SQL tạo bảng đó trong `database/gold/` |

Thử endpoint trực tiếp, bỏ qua frontend: http://localhost:8000/docs → *Try it out*.

## 4. Frontend

| Triệu chứng | Tìm ở |
|---|---|
| Màn hình trắng | F12 → Console → lỗi chỉ ra file `src/...` |
| Lỗi TypeScript khi `npm run build` | Đúng file và dòng in ra; thường do `src/types/api.ts` lệch với backend |
| `Không gọi được backend` | Backend chưa chạy, hoặc `BACKEND_PORT` trong `.env` khác cổng uvicorn |
| Gọi API bị 404 | Đường dẫn trong `src/api/endpoints.ts` sai |
| Dữ liệu hiển thị sai nhưng API đúng | Component trong `src/pages/` hoặc `src/components/` |
| Trang mới không hiện trên sidebar | Chưa thêm vào `src/routes.tsx` |

F12 → **Network** → bấm vào request `/api/...` để xem backend thực sự trả về gì.

## 5. Số liệu sai

Truy ngược theo các layer (data lineage): **Gold → Silver → Bronze → file CSV**.

```sql
-- So sánh số dòng qua các layer
SELECT 'bronze' AS layer, count(*) FROM bronze.hotel_bookings
UNION ALL SELECT 'silver', count(*) FROM silver.hotel_bookings;
-- Tra 1 booking cụ thể ở mọi layer
SELECT * FROM bronze.hotel_bookings WHERE _source_row = 42;
SELECT * FROM silver.hotel_bookings WHERE booking_id = 42;
```

| Lỗi hay gặp | Nguyên nhân |
|---|---|
| ADR hoặc tỉ lệ hủy tổng hợp bị lệch | Lấy `avg(adr)` thay vì `sum(revenue)/sum(nights)` (measure non-additive) |
| Doanh thu bị nhân lên | JOIN với dimension bị trùng khóa (dimension có 2 dòng cùng natural key) |
| Doanh thu tính cả booking đã hủy | Thiếu `WHERE NOT is_canceled` |
| Mô hình ML chính xác gần 100% | **Data leakage**: đang dùng `reservation_status` làm feature |

## 6. CI (GitHub Actions) đỏ

Vào tab **Actions** trên GitHub → bấm vào lần chạy đỏ → job đỏ:
- **Python (lint + test)**: chạy `ruff check .` và `pytest` ở máy mình để xem lỗi.
- **ETL pipeline**: chạy `python -m etl.run_pipeline` ở máy mình. CI giữ `data/raw/` bằng cache; muốn CI tải lại thì sửa code trong `etl/extract/`.
- **Docker demo**: chạy các lệnh ở §2b; log của mọi container nằm ở bước cuối của job.
- **Frontend**: chạy `cd frontend && npm run lint && npm run build`.

---

**Vẫn chưa sửa được?** Gửi vào nhóm: (1) lệnh đã chạy, (2) **toàn bộ** log lỗi, (3) đã thử những gì.
