# Hướng dẫn đóng góp (CONTRIBUTING)

Quy trình làm việc chung của nhóm. Đọc hết **một lần** trước khi code.

---

## 1. Phân công theo thành phần

Mỗi thư mục có **một người phụ trách chính** (owner). Owner review PR chạm vào thư mục đó.
Ai cũng được sửa mọi chỗ, nhưng phải được owner duyệt.

| Thư mục | Phụ trách chính | Hỗ trợ |
|---|---|---|
| `database/` (bronze/silver/gold, checks) | _TBD_ | |
| `etl/` | _TBD_ | |
| `ml/` | _TBD_ | |
| `backend/` | _TBD_ | |
| `frontend/` | _TBD_ | |
| `docs/`, `deliverables/` (báo cáo, slide, video) | _Cả nhóm_ | |

> Đề yêu cầu báo cáo đóng góp của từng thành viên (Appendix 1. Teamwork report). Commit và PR rõ ràng chính là bằng chứng.

---

## 2. Quy trình Git

### Nhánh (branch)
- `main`: luôn chạy được. **Không push thẳng**, chỉ merge qua Pull Request.
- Nhánh làm việc tạo từ `main`, đặt tên `<loại>/<thư-mục>-<mô-tả-ngắn>`:

| Ví dụ | Khi nào |
|---|---|
| `feat/gold-dim-date` | Thêm tính năng |
| `fix/etl-header-mismatch` | Sửa lỗi |
| `docs/report-chapter-3` | Tài liệu, báo cáo |
| `refactor/backend-kpi-service` | Cải tổ code, không đổi hành vi |

### Commit: theo [Conventional Commits](https://www.conventionalcommits.org/)
```
<loại>(<scope>): <mô tả ngắn, thì hiện tại>
```
- **loại**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
- **scope**: tên thư mục hoặc layer: `database`, `bronze`, `silver`, `gold`, `checks`, `etl`, `ml`, `backend`, `frontend`, `docs`

Ví dụ:
```
feat(gold): add fact_booking with surrogate keys
fix(silver): handle 'NA' in children column
feat(frontend): add KPI cards to overview page
docs(report): write chapter 2 business problem
```

### Các bước làm một việc
```bash
git checkout main && git pull
```
```bash
git checkout -b feat/gold-dim-date
```
Code, rồi commit nhỏ và thường xuyên:
```bash
git add database/gold/10_dim_date.sql && git commit -m "feat(gold): add dim_date"
```
```bash
git push -u origin feat/gold-dim-date
```
Sau đó mở Pull Request trên GitHub, điền template, và nhờ owner review.

### Pull Request
- Một PR làm **một việc**, nên dưới khoảng 400 dòng thay đổi.
- Phải qua **CI xanh** (lint, test, chạy pipeline, build frontend).
- Ít nhất **1 người duyệt** trước khi merge. Dùng **Squash and merge**.
- Sửa giao diện thì đính kèm ảnh chụp màn hình.

---

## 3. Quy ước theo thành phần

### 🗄️ `database/`: SQL
- **Tên file**: `NN_ten_bang.sql` (2 chữ số, chữ thường, gạch dưới). Pipeline chạy theo **thứ tự tên file**.
- **Idempotent**: chạy lại không lỗi. Bảng full-load dùng `DROP TABLE IF EXISTS` rồi `CREATE TABLE`.
- **Header bắt buộc** ở đầu mỗi file: tên bảng, nguồn, **grain**, các biến đổi chính (xem `database/silver/01_hotel_bookings.sql`).
- Quy ước số ở gold: `1x` = dimension, `3x` = fact, `5x` = KPI/view.
- Đặt tên: bảng `dim_*`, `fact_*`, `kpi_*`, `ml_*`; khóa thay thế `<dim>_key`; cột cờ `is_*`; ngày `*_date`.
- File check: dòng đầu `-- severity: error|warning`, câu SELECT trả về **các dòng vi phạm**.
- Sau khi sửa: chạy `python -m etl.run_pipeline --from <layer>` và cập nhật `docs/DATA_DICTIONARY.md`.

### ⚙️ `etl/`: Python pipeline
- Không viết logic biến đổi dữ liệu bằng pandas ở đây. Biến đổi làm bằng SQL trong `database/`.
  `etl/` chỉ **tải về, nạp vào, điều phối**.
- Thêm nguồn mới:
  1. Viết `etl/extract/<ten_nguon>.py` có hàm `extract(target: Path)`
  2. Viết DDL `database/bronze/NN_<ten_nguon>.sql` (cột TEXT, khớp header CSV)
  3. Đăng ký trong `SOURCES` ở `etl/extract/__init__.py`
- Log bằng `logging.getLogger("etl.<module>")`, không dùng `print`.

### 🤖 `ml/`
- Notebook đặt tên `NN_<ten>_<chu-de>.ipynb`, ví dụ `01_an_eda-cancellation.ipynb`. **Clear output trước khi commit.**
- Code dùng lại hoặc code train chính thức viết thành `.py` trong `ml/`, không để trong notebook.
- Kết quả cho ứng dụng **ghi vào bảng `gold.ml_*`**. Backend chỉ đọc bảng đó.
- Ghi rõ metric đánh giá (AUC, MAPE…) vào `ml/README.md` để đưa vào chương Evaluation.

### 🔌 `backend/`
Thêm một endpoint, theo thứ tự:
1. `app/schemas/<chu_de>.py`: model Pydantic cho response
2. `app/repositories/<chu_de>_repo.py`: câu SQL (chỉ đọc `gold`/`meta`)
3. `app/services/<chu_de>_service.py`: logic, tính toán
4. `app/api/routes/<chu_de>.py`: endpoint HTTP, rồi include trong `app/api/router.py`
5. `tests/test_<chu_de>.py`

Route **không chứa SQL**; repository **không chứa logic nghiệp vụ**.

### 🖥️ `frontend/`
Thêm một trang:
1. `src/types/api.ts`: thêm type khớp schema backend
2. `src/api/endpoints.ts`: thêm hàm gọi API
3. `src/pages/<Ten>Page.tsx`: trang, dùng hook `useApi`
4. `src/routes.tsx`: thêm 1 dòng (sidebar tự cập nhật)

- Component dùng lại để trong `src/components/` (`common/`, `charts/`, `filters/`, `layout/`).
- Tên file component: `PascalCase.tsx`; hook: `useXxx.ts`.
- Không gọi `fetch` trực tiếp trong component.

---

## 4. Trước khi push
```bash
ruff check . && pytest
```
```bash
cd frontend && npm run lint && npm run build
```
Nếu có sửa `database/` hoặc `etl/`:
```bash
python -m etl.run_pipeline
```

## 5. Quy tắc chung
- Không commit `.env`, dữ liệu (`data/raw/`), model (`ml/models/`), video.
- Không commit mật khẩu hay API key vào code.
- Gặp lỗi: xem `docs/TROUBLESHOOTING.md` trước, rồi hỏi trong nhóm kèm **log lỗi đầy đủ** và **lệnh đã chạy**.
