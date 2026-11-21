-- =============================================================================
-- gold.business_assumptions — Tham số giả định nghiệp vụ mà dataset không có.
-- Nguồn : nhóm tự đặt (xem docs/STAR_SCHEMA.md, mục 9)
-- Grain : 1 dòng = 1 tham số
-- Fact và view đọc giá trị MẶC ĐỊNH ở đây. Trang what-if cho người dùng nhập giá trị khác
-- (backend tính lại từ các cột gốc, không ghi vào bảng này).
-- Đổi giá trị mặc định: sửa file này rồi chạy `python -m etl.run_pipeline --from gold`.
-- =============================================================================

DROP TABLE IF EXISTS gold.business_assumptions CASCADE;

CREATE TABLE gold.business_assumptions (
    param_name   TEXT PRIMARY KEY,
    param_value  NUMERIC(10, 4) NOT NULL,
    unit         TEXT NOT NULL,
    description  TEXT NOT NULL
);

INSERT INTO gold.business_assumptions (param_name, param_value, unit, description) VALUES
    ('non_refund_deposit_rate', 0.20, 'ratio',
     'Tỉ lệ tiền cọc khách sạn giữ lại khi booking Non Refund bị hủy (so với booked_revenue). '
     'Dataset không có số tiền cọc thật nên đây là giả định.');
