-- =============================================================================
-- 00_schemas.sql — Tạo các schema theo kiến trúc Medallion + schema meta.
-- Idempotent: chạy lại bao nhiêu lần cũng được.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS bronze;  -- Dữ liệu thô, giữ nguyên như file nguồn (mọi cột là TEXT)
CREATE SCHEMA IF NOT EXISTS silver;  -- Dữ liệu đã làm sạch, ép kiểu, chuẩn hóa
CREATE SCHEMA IF NOT EXISTS gold;    -- Star schema (fact/dim) + bảng KPI/ML cho backend đọc
CREATE SCHEMA IF NOT EXISTS meta;    -- Thông tin vận hành pipeline (log, chất lượng dữ liệu)

COMMENT ON SCHEMA bronze IS 'Raw layer: dữ liệu nguồn nguyên bản';
COMMENT ON SCHEMA silver IS 'Cleaned layer: dữ liệu sạch, đúng kiểu';
COMMENT ON SCHEMA gold   IS 'Serving layer: star schema + bảng phục vụ ứng dụng';
COMMENT ON SCHEMA meta   IS 'Pipeline metadata: log chạy ETL';
