# etl/: Pipeline điều phối

Code Python để **tải nguồn → nạp bronze → chạy SQL các layer → kiểm tra chất lượng**.
Biến đổi dữ liệu viết bằng SQL trong `database/`, **không** viết ở đây.

```
etl/
├── run_pipeline.py      ▶ Điểm chạy chính (CLI)
├── config.py            Đường dẫn + đọc .env
├── db.py                Kết nối DB, chạy file SQL
├── run_log.py           Ghi log vào meta.etl_run_log
├── quality.py           Chạy database/checks/
├── extract/             Mỗi nguồn dữ liệu = 1 file + đăng ký trong __init__.py (SOURCES)
│   ├── hotel_bookings.py   Hotel Booking Demand (mirror TidyTuesday)
│   ├── pt_holidays.py      Ngày lễ Bồ Đào Nha (thư viện holidays)
│   ├── countries.py        Mã quốc gia ISO 3166
│   └── weather.py          Thời tiết theo ngày Lisbon + Faro (Open-Meteo)
├── load/
│   └── bronze_loader.py CSV → bronze bằng COPY, kiểm tra header
├── Dockerfile           Image cho service `etl` trong docker-compose.yml (chạy pipeline 1 lần)
└── tests/
```

## Chạy (từ thư mục gốc repo)
```bash
python -m etl.run_pipeline                    # tất cả
python -m etl.run_pipeline --from silver      # từ silver trở đi
python -m etl.run_pipeline --steps checks     # chỉ kiểm tra chất lượng
python -m etl.run_pipeline --refresh-sources  # tải lại file nguồn
```

## Chạy trong Docker (không cần venv)
```bash
docker compose run --rm etl                   # cần DB đang chạy: docker compose up -d db
```
File nguồn tải trong container được giữ ở volume `rawdata` (không phải `data/raw/` trên máy).

## Thêm nguồn dữ liệu mới
1. `etl/extract/<ten>.py` với hàm `extract(target: Path) -> None` ghi file CSV vào `target`
2. `database/bronze/NN_<ten>.sql`: bảng bronze, cột TEXT khớp header CSV
3. Thêm `Source(...)` vào `SOURCES` trong `etl/extract/__init__.py`
4. Viết SQL làm sạch ở `database/silver/`
