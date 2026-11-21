# database/: Toàn bộ SQL của dự án

Mọi thay đổi về **cấu trúc bảng** và **biến đổi dữ liệu** đều nằm ở đây.
Pipeline (`etl/run_pipeline.py`) chạy các file theo **thứ tự thư mục, rồi đến thứ tự tên file**.

| Thư mục | Chạy ở bước | Nội dung | Quy tắc |
|---|---|---|---|
| `init/` | init (luôn chạy) | Tạo schema `bronze/silver/gold/meta`, bảng log | `IF NOT EXISTS` |
| `bronze/` | bronze | DDL bảng thô (TEXT), sau đó Python nạp CSV | Tên cột khớp header CSV |
| `silver/` | silver | `CREATE TABLE AS SELECT` làm sạch, ép kiểu | Không lọc dòng |
| `gold/` | gold | Star schema, KPI | Dim `1x` → fact `3x` → KPI `5x` |
| `checks/` | checks | Kiểm tra chất lượng: SELECT trả về các dòng vi phạm | Dòng đầu `-- severity: error\|warning` |

## Thêm/sửa một bảng
1. Tạo hoặc sửa file `NN_ten.sql` trong đúng layer, có header (tên bảng, nguồn, grain, biến đổi).
2. Chạy lại từ layer đó: `python -m etl.run_pipeline --from silver`
3. Cập nhật `docs/DATA_DICTIONARY.md`.

## Debug
- Lỗi in ra dạng `Bước 'silver/01_hotel_bookings.sql' lỗi: ...` nghĩa là mở đúng file đó.
- Chạy thử từng đoạn SQL trong psql, DBeaver hoặc VS Code SQLTools.
- Lịch sử chạy: `SELECT * FROM meta.etl_run_log ORDER BY log_id DESC LIMIT 20;`
