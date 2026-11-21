# Định nghĩa bài toán kinh doanh

> Đây là nội dung gốc cho **Chương 2: Business problem definition** của báo cáo và slide.

## 1. Bối cảnh tổ chức

Một tập đoàn khách sạn ở Bồ Đào Nha vận hành 2 cơ sở:
- **City Hotel**: khách sạn thành phố ở Lisbon
- **Resort Hotel**: khu nghỉ dưỡng ven biển ở Algarve

Dữ liệu đặt phòng 07/2015 – 08/2017 (119.390 booking) cho thấy các vấn đề sau:

| Vấn đề | Bằng chứng từ dữ liệu |
|---|---|
| **Tỉ lệ hủy phòng rất cao** | 37,0% tổng cộng; City Hotel 41,7%, Resort Hotel 27,8% |
| **Nhu cầu và giá biến động mạnh theo mùa** | Tháng 7–8 có nhiều lượt đến nhất; ADR của Resort tháng 8 khoảng 174 € so với tháng 1 khoảng 49 € (gấp ~3,5 lần) |
| **Phụ thuộc kênh trung gian** | 82% booking đến qua kênh TA/TO (đại lý du lịch, OTA); chỉ 12% đặt trực tiếp |
| **Dữ liệu phân tán, chưa có hệ thống phân tích tập trung** | Quyết định dựa vào kinh nghiệm và báo cáo Excel |

Phòng bị hủy sát ngày thì không bán lại kịp, nên mất doanh thu trực tiếp. Ngược lại, nếu overbooking
quá tay thì khách đến mà hết phòng, gây tốn chi phí đền bù và mất uy tín.

## 2. Người ra quyết định

| Người ra quyết định | Quyết định cụ thể | Tần suất |
|---|---|---|
| **Revenue Manager** | Mức overbooking theo tuần/phân khúc; áp đặt cọc cho booking rủi ro cao; điều chỉnh giá theo mùa | Hằng tuần |
| **Sales & Marketing Manager** | Phân bổ ngân sách theo kênh (OTA, direct, corporate) và thị trường quốc gia; thời điểm khuyến mãi | Hằng tháng/quý |
| **General Manager** | Đánh giá hiệu quả 2 khách sạn; ưu tiên chiến lược | Hằng tháng |
| **Bộ phận Reservations** | Gọi xác nhận lại các booking có nguy cơ hủy cao | Hằng ngày |

## 3. Mục tiêu kỳ vọng

| # | Mục tiêu | Cách đo |
|---|---|---|
| G1 | Cung cấp cái nhìn tập trung về KPI (doanh thu, room-nights, ADR, tỉ lệ hủy) theo nhiều chiều | Dashboard có lọc/drill-down theo khách sạn, thời gian, kênh, quốc gia |
| G2 | Dự đoán booking nào sẽ hủy | AUC ≥ 0,85 trên tập test theo thời gian (năm 2017) |
| G3 | Dự báo nhu cầu (room-nights) theo tuần | MAPE trên giai đoạn backtest |
| G4 | Hỗ trợ quyết định overbooking và đặt cọc | Mô phỏng what-if: doanh thu cứu được so với rủi ro hết phòng |
| G5 | Xác định kênh và thị trường giá trị nhất | Xếp hạng theo doanh thu thực (sau hủy), ADR, tỉ lệ hủy |

## 4. Phạm vi

**Trong phạm vi:** dữ liệu lịch sử của 2 khách sạn; phân tích mô tả, chẩn đoán, dự đoán, đề xuất; ứng dụng web tương tác.

**Ngoài phạm vi:** kết nối trực tiếp PMS thời gian thực; tối ưu giá động tự động.

**Giả định và hạn chế:**
- Dataset **không có số phòng** của mỗi khách sạn, nên occupancy và RevPAR chỉ tính được khi người dùng nhập công suất làm tham số.
- Không có dữ liệu chi phí (hoa hồng OTA, chi phí đền bù overbooking): đưa vào làm **tham số điều chỉnh được** trong what-if.
- Tên khách sạn đã được ẩn danh trong dataset gốc.

## 5. Giải pháp đề xuất (tóm tắt)

1. **Lakehouse** PostgreSQL theo kiến trúc Medallion: tích hợp dữ liệu booking, ngày lễ, thời tiết.
2. **Star schema** ở lớp Gold, phục vụ phân tích OLAP.
3. **Phân tích**: mô hình dự đoán hủy, mô hình dự báo nhu cầu.
4. **Ứng dụng web** cho từng người ra quyết định: dashboard KPI, rủi ro hủy, dự báo, mô phỏng what-if.

Chi tiết kỹ thuật: [`ARCHITECTURE.md`](ARCHITECTURE.md)
