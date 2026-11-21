-- =============================================================================
-- gold.dim_hotel — Dimension khách sạn (conformed)
-- Nguồn : DISTINCT silver.hotel_bookings.hotel_name + thuộc tính mô tả từ bài báo gốc
--         (City Hotel ở Lisbon, Resort Hotel ở Algarve; tọa độ dùng để nối thời tiết sau này)
-- Grain : 1 dòng = 1 khách sạn (2 dòng)
-- Cố ý KHÔNG có cột số phòng: dataset không có công suất (quy tắc 10 trong CLAUDE.md).
-- =============================================================================

DROP TABLE IF EXISTS gold.dim_hotel CASCADE;

CREATE TABLE gold.dim_hotel AS
WITH hotels AS (
    SELECT DISTINCT hotel_name FROM silver.hotel_bookings
)
SELECT
    ROW_NUMBER() OVER (ORDER BY hotel_name)::INT                                   AS hotel_key,
    hotel_name,
    CASE hotel_name WHEN 'City Hotel' THEN 'City' WHEN 'Resort Hotel' THEN 'Resort' ELSE 'Unknown' END
                                                                                   AS hotel_type,
    CASE hotel_name WHEN 'City Hotel' THEN 'Lisbon' WHEN 'Resort Hotel' THEN 'Algarve' ELSE 'Unknown' END
                                                                                   AS city,
    'PRT'::TEXT                                                                    AS country_code,
    CASE hotel_name WHEN 'City Hotel' THEN 38.72230 WHEN 'Resort Hotel' THEN 37.01930 END::NUMERIC(8, 5)
                                                                                   AS latitude,
    CASE hotel_name WHEN 'City Hotel' THEN -9.13930 WHEN 'Resort Hotel' THEN -7.93040 END::NUMERIC(8, 5)
                                                                                   AS longitude
FROM hotels;

ALTER TABLE gold.dim_hotel ADD PRIMARY KEY (hotel_key);
ALTER TABLE gold.dim_hotel ADD CONSTRAINT uq_dim_hotel_name UNIQUE (hotel_name);
