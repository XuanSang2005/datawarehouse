# CLAUDE.md

Hướng dẫn cho AI assistant (Claude Code) và cũng là "luật chơi" ngắn gọn cho người mới vào repo.

## Dự án
Hệ thống hỗ trợ quyết định (DSS) cho chuỗi khách sạn: lakehouse PostgreSQL (bronze → silver → gold)
cộng web app (FastAPI + React). Đây là đồ án môn CO4031. Bài toán: giảm thiệt hại do hủy phòng và tối ưu doanh thu.
Dataset chính là Hotel Booking Demand (Antonio et al., 2019). Xem `docs/BUSINESS_PROBLEM.md`.

## Bản đồ repo: mỗi loại việc chỉ có MỘT chỗ
| Việc | Chỗ |
|---|---|
| Tạo/sửa bảng, biến đổi dữ liệu, KPI | `database/<layer>/NN_name.sql` |
| Kiểm tra chất lượng dữ liệu | `database/checks/NN_name.sql` |
| Thêm nguồn dữ liệu mới | `etl/extract/` + đăng ký trong `etl/extract/__init__.py` + DDL trong `database/bronze/` |
| Điều phối pipeline | `etl/run_pipeline.py` |
| Mô hình ML / notebook | `ml/` |
| Endpoint API | `backend/app/api/routes/` → `services/` → `repositories/` |
| Trang giao diện | `frontend/src/pages/` + đăng ký trong `frontend/src/routes.tsx` |
| Cấu hình | `.env` ở thư mục gốc (mẫu: `.env.example`), dùng chung cho tất cả |

## Lệnh
```bash
docker compose up -d db                              # bật DB
python -m etl.run_pipeline [--from silver]           # chạy pipeline (từ thư mục gốc)
cd backend && uvicorn app.main:app --reload          # backend :8000
cd frontend && npm run dev                           # frontend :5173 (proxy /api -> :8000)
pytest && ruff check .                               # test + lint Python
cd frontend && npm run lint && npm run build         # lint + build FE
```

## Quy tắc bắt buộc
1. **SQL chỉ nằm trong `database/`.** Ngoại lệ duy nhất: câu SELECT trong `backend/app/repositories/`.
2. **File SQL đánh số `NN_ten.sql` và idempotent** (dùng `DROP ... IF EXISTS` / `CREATE ... IF NOT EXISTS`). Pipeline chạy theo thứ tự tên file.
3. **Bronze giữ nguyên nguồn**: mọi cột TEXT, không làm sạch. Làm sạch ở silver, mô hình hóa ở gold.
4. **Backend chỉ đọc schema `gold` và `meta`**, không đọc bronze/silver, không ghi dữ liệu nghiệp vụ, không train model.
5. **Phân tầng backend**: routes (HTTP) → services (logic) → repositories (SQL). Route không chứa SQL.
6. **Frontend không gọi `fetch` trực tiếp**, mà phải qua `src/api/endpoints.ts`. Kiểu dữ liệu trong `src/types/api.ts` phải khớp `backend/app/schemas/`.
7. **Chống data leakage**: không dùng `reservation_status`, `reservation_status_date` (và cân nhắc `assigned_room_type`, `booking_changes`) làm feature dự đoán hủy. Chia train/test theo thời gian.
8. **Measure non-additive** (ADR, tỉ lệ hủy) phải tính lại từ tổng (`sum(revenue)/sum(nights)`), không lấy trung bình của trung bình.
9. Không commit `.env`, `data/raw/*`, `ml/models/*`, video.
10. Dataset không có số phòng của khách sạn: occupancy và RevPAR chỉ tính khi người dùng nhập công suất làm tham số.

## Quy ước
- Tài liệu và comment: tiếng Việt. Tên biến, bảng, cột: tiếng Anh, `snake_case` (Python/SQL), `camelCase` (TS).
- Commit theo Conventional Commits, scope là tên thư mục: `feat(gold): add dim_date`, `fix(backend): ...`. Xem `CONTRIBUTING.md`.
- Thêm/sửa bảng → cập nhật `docs/DATA_DICTIONARY.md`. Đổi kiến trúc → cập nhật `docs/ARCHITECTURE.md`.
- Lỗi thường gặp và nơi tìm: `docs/TROUBLESHOOTING.md`.
