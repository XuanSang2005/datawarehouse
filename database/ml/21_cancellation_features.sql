-- =============================================================================
-- Dữ liệu đầu vào cho mô hình dự đoán hủy (E3): CHỈ là câu SELECT, không tạo bảng.
-- Đọc bởi: ml/cancellation/features.py (load_dataset). Không chạy bởi etl/run_pipeline.py.
-- Grain : 1 dòng = 1 booking của gold.fact_booking (toàn bộ booking đều được chấm điểm).
-- Cột   : booking_id + nhãn is_canceled + cột dùng để chia tập (arrival_date) + các cột
--         biết được TẠI THỜI ĐIỂM ĐẶT PHÒNG.
-- ⛔ Cố ý KHÔNG chọn cột suy ra từ kết quả hủy (xem comment đầu database/gold/30_fact_booking.sql)
--    và cột chỉ biết sau khi đặt (phòng thực nhận, số lần sửa booking, số ngày chờ).
--    Danh sách đầy đủ + lý do: ml/cancellation/features.py (LEAKAGE_COLUMNS).
--    ml/tests/test_cancellation_features.py kiểm tra file này không nhắc tới cột cấm nào.
-- =============================================================================

SELECT
    f.booking_id,
    f.is_canceled,
    d.full_date                            AS arrival_date,

    -- Khách sạn và thời gian đến
    h.hotel_name,
    d.day_of_week                          AS arrival_day_of_week,
    d.season                               AS arrival_season,
    d.is_holiday                           AS arrival_is_holiday,

    -- Đặt trước bao lâu, ở bao lâu, bao nhiêu khách
    f.lead_time,
    f.weekend_nights,
    f.week_nights,
    f.total_nights,
    f.adults,
    f.children,
    f.babies,

    -- Kênh bán và đại lý
    ch.market_segment,
    ch.distribution_channel,
    ag.agent_id,
    f.company_id,

    -- Khách hàng
    co.country_code,
    co.market_group,
    bp.meal,
    bp.deposit_type,
    bp.customer_type,
    bp.is_repeated_guest,
    bp.party_type,
    f.previous_cancellations,
    f.previous_bookings_not_canceled,

    -- Phòng đặt và giá
    rr.room_type_code                      AS reserved_room_type,
    f.adr,
    f.total_of_special_requests
FROM gold.fact_booking            AS f
JOIN gold.dim_hotel               AS h  ON h.hotel_key = f.hotel_key
JOIN gold.dim_date                AS d  ON d.date_key = f.arrival_date_key
JOIN gold.dim_channel             AS ch ON ch.channel_key = f.channel_key
JOIN gold.dim_agent               AS ag ON ag.agent_key = f.agent_key
JOIN gold.dim_country             AS co ON co.country_key = f.country_key
JOIN gold.dim_booking_profile     AS bp ON bp.booking_profile_key = f.booking_profile_key
JOIN gold.dim_room_type           AS rr ON rr.room_type_key = f.reserved_room_type_key
ORDER BY f.booking_id;
