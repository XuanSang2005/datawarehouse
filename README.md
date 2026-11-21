# Tourism DSS: Hệ thống hỗ trợ quyết định cho chuỗi khách sạn

> Đồ án môn **Data Warehouses and Decision Support Systems (CO4031)**
> Chủ đề: *Build a decision support solution utilizing a data warehouse/lake/lakehouse and data analytics*, lĩnh vực **Tourism**.

Một **lakehouse** (PostgreSQL, kiến trúc Bronze → Silver → Gold) cùng một **ứng dụng web** giúp tập đoàn khách sạn
**giảm thiệt hại do hủy phòng** và **tối ưu doanh thu theo mùa**.

| Người ra quyết định | Hệ thống hỗ trợ quyết định gì |
|---|---|
| Revenue Manager | Mức overbooking, chính sách đặt cọc, giá theo mùa |
| Sales & Marketing Manager | Phân bổ ngân sách theo kênh bán và thị trường |
| General Manager | Theo dõi KPI, so sánh 2 khách sạn |
| Bộ phận Reservations | Danh sách booking rủi ro cao cần gọi xác nhận |

Chi tiết bài toán: [`docs/BUSINESS_PROBLEM.md`](docs/BUSINESS_PROBLEM.md)

---

## Kiến trúc tóm tắt

```
 Nguồn dữ liệu          ETL (Python + SQL)                PostgreSQL                  Ứng dụng
┌──────────────┐     ┌──────────────────┐     ┌────────────────────────────┐     ┌──────────────┐
│ hotel_bookings│ ──▶ │ etl/extract      │ ──▶ │ bronze ─▶ silver ─▶ gold   │ ◀── │ backend      │ ◀── frontend
│ pt_holidays   │     │ etl/load         │     │ (database/*.sql)           │     │ FastAPI :8000│     React :5173
│ (weather...)  │     │ etl/run_pipeline │     │ meta (log pipeline)        │     └──────────────┘
└──────────────┘     └──────────────────┘     └────────────────────────────┘
                                                        ▲
                                              ml/ (train) ghi kết quả vào gold.ml_*
```

Chi tiết: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

---

## Cấu trúc thư mục

```
datawarehouse/
├── database/          🗄️  DB: TOÀN BỘ SQL (tạo schema, bảng, biến đổi, kiểm tra chất lượng)
│   ├── init/              Tạo schema bronze/silver/gold/meta + bảng log
│   ├── bronze/            DDL bảng thô (mọi cột TEXT)
│   ├── silver/            SQL làm sạch, ép kiểu
│   ├── gold/              SQL star schema (fact/dim) + KPI
│   └── checks/            SQL kiểm tra chất lượng dữ liệu
├── etl/               ⚙️  PIPELINE: code Python điều phối, tải và nạp dữ liệu
│   ├── extract/           Tải/sinh file nguồn vào data/raw/
│   ├── load/              Nạp CSV vào bronze (COPY)
│   ├── run_pipeline.py    ▶ Điểm chạy chính
│   └── tests/
├── ml/                🤖  PHÂN TÍCH: notebook khám phá + mô hình dự đoán
├── backend/           🔌  BE: FastAPI, chỉ đọc gold/meta, trả JSON
│   └── app/
│       ├── api/routes/    Endpoint HTTP
│       ├── services/      Logic nghiệp vụ (what-if, khuyến nghị)
│       ├── repositories/  Câu SQL
│       ├── schemas/       Kiểu dữ liệu request/response (Pydantic)
│       └── core/          Cấu hình, kết nối DB, logging
├── frontend/          🖥️  FE: React + Vite + TypeScript
│   └── src/
│       ├── pages/         Mỗi trang = 1 file
│       ├── components/    Thành phần giao diện dùng lại
│       ├── api/           Hàm gọi backend
│       ├── hooks/         React hooks dùng chung
│       └── types/         Kiểu dữ liệu (khớp backend/schemas)
├── data/raw/          📦  File nguồn tải về (KHÔNG commit)
├── docs/              📚  Tài liệu: kiến trúc, bài toán, từ điển dữ liệu, xử lý lỗi
├── deliverables/      📑  Sản phẩm nộp: slide, báo cáo, link video
├── docker-compose.yml     PostgreSQL (+ backend/frontend khi demo)
├── Makefile               Lối tắt lệnh
└── .env.example           Mẫu cấu hình -> copy thành .env
```

**Có lỗi thì tìm ở đâu?** Xem [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md).

---

## Cài đặt lần đầu

### Yêu cầu
- **Python 3.11+**, **Node.js 20+**, **Docker Desktop**
- Git, VS Code (khuyến nghị; repo có sẵn gợi ý extension)

### Các bước

**1. Clone repo và tạo file cấu hình**
```bash
git clone https://github.com/XuanSang2005/datawarehouse.git
```
```bash
cd datawarehouse
```
```bash
cp .env.example .env
```

**2. Tạo môi trường Python** (1 venv duy nhất ở thư mục gốc)
```bash
python -m venv .venv
```
macOS/Linux:
```bash
source .venv/bin/activate
```
Windows (PowerShell):
```bash
.venv\Scripts\Activate.ps1
```
```bash
pip install -r requirements-dev.txt
```

**3. Cài frontend**
```bash
cd frontend && npm install && cd ..
```

**4. Bật database**
```bash
docker compose up -d db
```

**5. Chạy pipeline**: tự tải dữ liệu, nạp bronze → silver → gold, rồi kiểm tra chất lượng
```bash
python -m etl.run_pipeline
```

**6. Chạy ứng dụng** (mở 2 terminal)
```bash
cd backend && uvicorn app.main:app --reload --port 8000
```
```bash
cd frontend && npm run dev
```

Mở http://localhost:5173, vào trang **Trạng thái hệ thống**: nếu mọi thứ màu xanh là cài đặt thành công.
Tài liệu API tự sinh có ở http://localhost:8000/docs.

> Có `make` (macOS/Linux)? Gõ `make help` để xem các lối tắt: `make db-up`, `make etl`, `make backend`…

---

## Lệnh hay dùng

| Việc cần làm | Lệnh |
|---|---|
| Chạy lại toàn bộ pipeline | `python -m etl.run_pipeline` |
| Chỉ chạy lại silver + gold (sau khi sửa SQL) | `python -m etl.run_pipeline --from silver` |
| Chạy một số bước | `python -m etl.run_pipeline --steps gold checks` |
| Tải lại file nguồn | `python -m etl.run_pipeline --refresh-sources` |
| Test Python | `pytest` |
| Lint | `ruff check .` và `cd frontend && npm run lint` |
| Reset sạch database | `docker compose down -v && docker compose up -d db` |
| Chạy cả hệ thống bằng Docker (demo) | `docker compose --profile app up -d --build` |

---

## Dữ liệu

| Nguồn | Mô tả | Cách lấy |
|---|---|---|
| **Hotel Booking Demand** | 119.390 booking, City Hotel (Lisbon) và Resort Hotel (Algarve), 07/2015–08/2017 | Tự tải (mirror công khai của Kaggle) |
| **Ngày lễ Bồ Đào Nha** | 2013–2018 | Sinh bằng thư viện `holidays` |
| *(dự kiến)* Thời tiết lịch sử | Lisbon, Faro | Open-Meteo Archive API |

Mô tả từng cột: [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md)

> Nguồn: N. Antonio, A. de Almeida, L. Nunes, "Hotel booking demand datasets", *Data in Brief*, vol. 22, pp. 41–49, 2019.

---

## Tài liệu

| File | Nội dung |
|---|---|
| [`docs/BUSINESS_PROBLEM.md`](docs/BUSINESS_PROBLEM.md) | Bối cảnh, người ra quyết định, mục tiêu |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Kiến trúc, luồng dữ liệu, star schema, lý do chọn công nghệ |
| [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md) | Ý nghĩa từng bảng và từng cột |
| [`docs/GLOSSARY.md`](docs/GLOSSARY.md) | Thuật ngữ data warehouse dùng trong dự án |
| [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) | Lỗi gì, tìm ở đâu, sửa thế nào |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Quy trình làm việc nhóm: branch, commit, PR, quy ước code |
| [`deliverables/README.md`](deliverables/README.md) | Hạn nộp và quy tắc đặt tên file nộp |

## Thành viên

| Họ tên | MSSV | Vai trò |
|---|---|---|
| _TBD_ | | |
