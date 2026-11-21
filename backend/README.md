# backend/: FastAPI

API đọc dữ liệu từ schema `gold` và `meta`, xử lý logic (what-if, khuyến nghị), trả JSON cho frontend.

```
backend/
├── app/
│   ├── main.py              Khởi tạo app, bắt lỗi DB tập trung (→ HTTP 503)
│   ├── api/
│   │   ├── router.py        Gom router, prefix /api
│   │   └── routes/          Endpoint HTTP: KHÔNG chứa SQL
│   ├── services/            Logic nghiệp vụ, tính toán
│   ├── repositories/        CHỈ câu SQL (đọc gold/meta)
│   ├── schemas/             Pydantic models (hợp đồng với frontend)
│   └── core/                config (.env), db (engine), logging
├── tests/
├── requirements.txt
└── Dockerfile
```

## Chạy
```bash
cd backend && uvicorn app.main:app --reload --port 8000
```
Swagger UI để thử API: http://localhost:8000/docs

## Endpoint hiện có
Chi tiết tham số và kiểu trả về: Swagger UI `/docs`. Kiểu TypeScript tương ứng: `frontend/src/types/api.ts`.

**Bộ lọc dùng chung** (endpoint có dấu ✓ ở cột Lọc): `hotel_key`, `date_from`, `date_to` (theo **ngày đến**),
`channel_group` (vd `OTA`), `country_code` (ISO alpha-3, `UNK` = không rõ quốc gia).

| Method | Path | Lọc | Mô tả | Mục tiêu |
|---|---|---|---|---|
| GET | `/api/health` | | Trạng thái API và kết nối DB | |
| GET | `/api/pipeline/runs?limit=50` | | Log các bước ETL gần nhất | |
| GET | `/api/filters` | | Danh mục cho FilterBar: khách sạn (kèm `peak_rooms_occupied`), nhóm kênh, phân khúc, quốc gia, khoảng ngày | |
| GET | `/api/kpi/summary` | ✓ | KPI tổng + tách theo khách sạn (City vs Resort) | G1 |
| GET | `/api/kpi/timeseries?grain=year\|quarter\|month\|week&by_hotel=` | ✓ | Chuỗi KPI để drill-down | G1 |
| GET | `/api/cancellation/breakdown?by=lead_time\|channel\|deposit_type\|country\|market_segment\|customer_type&top_n=` | ✓ | Tỉ lệ hủy theo chiều | G2 |
| GET | `/api/cancellation/high-risk?risk_band=High\|Medium\|Low\|All&min_probability=&test_set_only=true&sort=probability\|expected_loss&page=&page_size=` | ✓ | Booking rủi ro hủy cao, phân trang; kèm `total`, `booked_revenue_total`, `expected_loss_total` của mọi trang | G2 |
| GET | `/api/cancellation/model-metrics` | | AUC, precision, recall, F1, ngưỡng của model hủy | G2 |
| GET | `/api/forecast?hotel_key=&model_version=` | | Room-nights tuần: dự báo, khoảng 80%, thực tế, lịch sử | G3 |
| GET | `/api/forecast/metrics` | | MAPE model chính và baseline | G3 |
| POST | `/api/what-if` | | Mô phỏng overbooking + đặt cọc theo rủi ro, đường cong lợi ích, mức gợi ý | G4 |
| GET | `/api/channels/ranking?sort_by=&top_n=&min_bookings=` | ✓ | Xếp hạng nhóm kênh | G5 |
| GET | `/api/markets/ranking?sort_by=&top_n=&min_bookings=100` | ✓ | Xếp hạng quốc gia | G5 |

**Mã lỗi**: `404` + `hint` khi dữ liệu chưa có (vd chưa chạy script ML), `422` khi tham số sai, `503` khi lỗi DB.

**Quy ước số liệu**: tiền là EUR; tỉ lệ trả dạng 0–1; tỉ lệ/ADR tính từ tổng (`sum/sum`), `null` nếu mẫu số = 0.

### Ví dụ what-if
```bash
curl -s -X POST localhost:8000/api/what-if -H 'Content-Type: application/json' \
  -d '{"hotel_key": 1, "capacity": 230, "overbooking_pct": 0.05, "walk_cost": 150, "ota_commission": 0.15}'
```
Mặc định mô phỏng trên năm 2017 (tập test của model hủy, điểm rủi ro ngoài mẫu). Ngưỡng cọc mặc định là ngưỡng
`High` của model (`gold.ml_model_metrics`), tỉ lệ cọc mặc định lấy từ `gold.business_assumptions`.
Công thức: docstring của `app/services/what_if_service.py`.

## Thêm endpoint
`schemas/` → `repositories/` → `services/` → `api/routes/` → include trong `api/router.py` → `tests/`.
Nhớ cập nhật `frontend/src/types/api.ts` cho khớp schema.
