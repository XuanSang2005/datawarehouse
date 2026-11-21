-- =============================================================================
-- gold.dim_room_type — Dimension loại phòng (role-playing: reserved / assigned)
-- Nguồn : UNION reserved_room_type và assigned_room_type từ silver.hotel_bookings
-- Grain : 1 dòng = 1 mã loại phòng (12 dòng; mã đã bị ẩn danh trong nguồn)
-- =============================================================================

DROP TABLE IF EXISTS gold.dim_room_type CASCADE;

CREATE TABLE gold.dim_room_type AS
WITH codes AS (
    SELECT reserved_room_type AS room_type_code FROM silver.hotel_bookings
    UNION
    SELECT assigned_room_type FROM silver.hotel_bookings
)
SELECT
    ROW_NUMBER() OVER (ORDER BY room_type_code)::INT  AS room_type_key,
    room_type_code,
    'Room type ' || room_type_code                    AS room_type_label
FROM codes;

ALTER TABLE gold.dim_room_type ADD PRIMARY KEY (room_type_key);
ALTER TABLE gold.dim_room_type ADD CONSTRAINT uq_dim_room_type_code UNIQUE (room_type_code);
