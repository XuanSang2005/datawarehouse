-- =============================================================================
-- gold.dim_room_type — Room type dimension (role-playing: reserved / assigned)
-- Source: UNION of reserved_room_type and assigned_room_type from silver.hotel_bookings
-- Grain : 1 row = 1 room type code (12 rows; codes are anonymized in the source)
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
