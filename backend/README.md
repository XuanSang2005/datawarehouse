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
| Method | Path | Mô tả |
|---|---|---|
| GET | `/api/health` | Trạng thái API và kết nối DB |
| GET | `/api/pipeline/runs?limit=50` | Log các bước ETL gần nhất |

## Thêm endpoint
`schemas/` → `repositories/` → `services/` → `api/routes/` → include trong `api/router.py` → `tests/`.
Nhớ cập nhật `frontend/src/types/api.ts` cho khớp schema.
