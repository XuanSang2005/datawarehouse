-- =============================================================================
-- silver.hotel_bookings — Booking đã ép kiểu và chuẩn hóa giá trị rỗng.
-- Nguồn : bronze.hotel_bookings
-- Grain : 1 dòng = 1 booking
-- Biến đổi chính:
--   * booking_id     : khóa định danh tự sinh (dataset gốc không có) = _source_row
--   * 'NULL'/'NA'/'Undefined' : chuyển thành NULL thật (riêng meal: Undefined -> 'SC')
--   * arrival_date   : ghép từ year + month (tên tháng) + day_of_month
--   * booking_date   : arrival_date - lead_time (ngày khách đặt phòng)
--   * total_nights   : weekend + week nights
-- KHÔNG lọc bỏ dòng bất thường ở đây -> xem database/checks/ để biết dòng nào có vấn đề.
-- ⚠ reservation_status / reservation_status_date chứa KẾT QUẢ booking:
--   giữ lại cho phân tích mô tả, nhưng TUYỆT ĐỐI không dùng làm feature cho mô hình dự đoán hủy.
-- =============================================================================

DROP TABLE IF EXISTS silver.hotel_bookings;

CREATE TABLE silver.hotel_bookings AS
WITH src AS (
    SELECT
        b.*,
        make_date(
            b.arrival_date_year::INT,
            EXTRACT(MONTH FROM to_date(b.arrival_date_month, 'FMMonth'))::INT,
            b.arrival_date_day_of_month::INT
        ) AS arrival_date
    FROM bronze.hotel_bookings AS b
)
SELECT
    _source_row                                                   AS booking_id,
    hotel                                                         AS hotel_name,
    (is_canceled = '1')                                           AS is_canceled,
    lead_time::INT                                                AS lead_time,
    arrival_date,
    (arrival_date - lead_time::INT)                               AS booking_date,
    arrival_date_week_number::INT                                 AS arrival_week_number,
    stays_in_weekend_nights::INT                                  AS weekend_nights,
    stays_in_week_nights::INT                                     AS week_nights,
    (stays_in_weekend_nights::INT + stays_in_week_nights::INT)    AS total_nights,
    adults::INT                                                   AS adults,
    COALESCE(NULLIF(NULLIF(children, 'NA'), 'NULL')::INT, 0)      AS children,
    babies::INT                                                   AS babies,
    CASE WHEN meal = 'Undefined' THEN 'SC' ELSE meal END          AS meal,  -- theo bài báo gốc: Undefined = SC
    NULLIF(NULLIF(country, 'NULL'), 'NA')                         AS country_code,
    NULLIF(market_segment, 'Undefined')                           AS market_segment,
    NULLIF(distribution_channel, 'Undefined')                     AS distribution_channel,
    (is_repeated_guest = '1')                                     AS is_repeated_guest,
    previous_cancellations::INT                                   AS previous_cancellations,
    previous_bookings_not_canceled::INT                           AS previous_bookings_not_canceled,
    reserved_room_type,
    assigned_room_type,
    booking_changes::INT                                          AS booking_changes,
    deposit_type,
    NULLIF(NULLIF(agent, 'NULL'), 'NA')::INT                      AS agent_id,
    NULLIF(NULLIF(company, 'NULL'), 'NA')::INT                    AS company_id,
    days_in_waiting_list::INT                                     AS days_in_waiting_list,
    customer_type,
    adr::NUMERIC(10, 2)                                           AS adr,
    required_car_parking_spaces::INT                              AS required_car_parking_spaces,
    total_of_special_requests::INT                                AS total_of_special_requests,
    reservation_status,
    reservation_status_date::DATE                                 AS reservation_status_date
FROM src;

ALTER TABLE silver.hotel_bookings ADD PRIMARY KEY (booking_id);
