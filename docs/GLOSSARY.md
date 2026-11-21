# Thuật ngữ (Glossary)

Các thuật ngữ data warehouse dùng trong dự án, kèm ví dụ cụ thể từ repo.

## Kiến trúc

| Thuật ngữ | Ý nghĩa | Trong dự án |
|---|---|---|
| **OLTP** | Hệ thống nghiệp vụ, ghi/sửa từng giao dịch | Phần mềm đặt phòng (PMS). File CSV là dữ liệu trích ra từ đây |
| **OLAP** | Hệ thống phân tích, tổng hợp lượng dữ liệu lớn | Lớp gold + dashboard |
| **Data Warehouse** | Kho dữ liệu sạch, tích hợp, hướng chủ đề, lưu theo thời gian | Schema `gold` |
| **Data Lake** | Kho dữ liệu thô, đủ mọi định dạng | `data/raw/` + schema `bronze` |
| **Lakehouse** | Kết hợp lake (thô, rẻ) và warehouse (có cấu trúc) | Toàn bộ hệ thống |
| **Medallion** | Chia 3 lớp Bronze (thô) → Silver (sạch) → Gold (sẵn sàng phân tích) | `database/bronze`, `silver`, `gold` |
| **Data Mart** | Phần nhỏ của DW cho một phòng ban | Các bảng `kpi_*` cho Revenue / Marketing |

## ETL

| Thuật ngữ | Ý nghĩa | Trong dự án |
|---|---|---|
| **Extract** | Lấy dữ liệu từ nguồn | `etl/extract/` |
| **Load** | Nạp vào kho | `etl/load/bronze_loader.py` (COPY) |
| **Transform** | Làm sạch, biến đổi | `database/silver/*.sql`, `database/gold/*.sql` |
| **ELT** | Nạp thô trước, biến đổi trong DB sau | Cách dự án đang làm |
| **Full load / Incremental load** | Nạp lại toàn bộ / chỉ nạp phần mới | Đang dùng full load |
| **Data quality check** | Kiểm tra dữ liệu bất thường | `database/checks/` |
| **Data lineage** | Truy vết nguồn gốc một con số | `_source_row` ở bronze = `booking_id` ở silver |
| **Orchestration** | Điều phối thứ tự các bước | `etl/run_pipeline.py` |

## Mô hình hóa chiều (Dimensional modeling)

| Thuật ngữ | Ý nghĩa | Ví dụ |
|---|---|---|
| **Fact table** | Bảng sự kiện, chứa số đo | `fact_booking` |
| **Dimension table** | Bảng ngữ cảnh: ai, khi nào, ở đâu, qua kênh nào | `dim_date`, `dim_hotel`, `dim_country` |
| **Grain** | Một dòng fact đại diện cho cái gì | 1 booking; hoặc 1 khách sạn × 1 đêm |
| **Measure** | Cột số trong fact | `revenue`, `total_nights`, `adr` |
| **Additive** | Cộng được theo mọi chiều | `revenue`, `room_nights` |
| **Semi-additive** | Không cộng theo thời gian | Số phòng đang có khách mỗi ngày |
| **Non-additive** | Không cộng được, phải tính lại từ thành phần | **ADR**, **tỉ lệ hủy** |
| **Natural key** | Mã từ nguồn | `country = 'PRT'` |
| **Surrogate key** | Khóa số tự sinh trong DW | `country_key = 17` |
| **Star schema** | Fact ở giữa, dimension nối thẳng vào | Mô hình gold |
| **Snowflake schema** | Dimension chuẩn hóa thành nhiều bảng | Không dùng |
| **Hierarchy** | Phân cấp trong dimension | Năm → Quý → Tháng → Tuần → Ngày |
| **Role-playing dimension** | Một dimension đóng nhiều vai | `dim_date` cho ngày đặt và ngày đến |
| **Degenerate dimension** | Mã định danh nằm trong fact, không có bảng riêng | `booking_id` |
| **Junk dimension** | Gom các cờ lặt vặt vào một bảng | `dim_booking_profile` (meal, deposit_type, customer_type) |
| **Conformed dimension** | Dimension dùng chung cho nhiều fact | `dim_date`, `dim_hotel` |
| **SCD Type 1 / Type 2** | Thuộc tính thay đổi: ghi đè / thêm dòng mới, giữ lịch sử | Thiết kế cho `dim_agent` |
| **Transaction fact** | Mỗi dòng là một sự kiện | `fact_booking` |
| **Periodic snapshot** | Chụp trạng thái theo chu kỳ | `fact_daily_occupancy` |
| **Accumulating snapshot** | Theo dõi vòng đời qua nhiều mốc | Đặt → hủy/đến → trả phòng |

## OLAP

| Thao tác | Ý nghĩa | Ví dụ |
|---|---|---|
| **Roll-up** | Gộp lên cấp cao hơn | Tháng → Năm |
| **Drill-down** | Đi xuống chi tiết hơn | Năm → Tháng → Tuần |
| **Slice** | Cố định một chiều | Chỉ City Hotel |
| **Dice** | Lọc nhiều chiều | City Hotel + OTA + 2016 |
| **Pivot** | Xoay trục | Đổi hàng và cột |

## KPI khách sạn

| KPI | Công thức |
|---|---|
| **Room-nights** | `weekend_nights + week_nights` |
| **Revenue** | `adr × total_nights` (chỉ booking không hủy) |
| **ADR** | `sum(revenue) / sum(room_nights)` |
| **Cancellation rate** | `số booking hủy / tổng số booking` |
| **Lead time** | Số ngày từ lúc đặt đến ngày đến |
| **LOS** | Số đêm lưu trú trung bình |
| **Occupancy** | `room_nights bán được / room_nights sẵn có` (cần nhập công suất) |
| **RevPAR** | `revenue / room_nights sẵn có` (cần nhập công suất) |

## Hỗ trợ ra quyết định

| Thuật ngữ | Ý nghĩa |
|---|---|
| **DSS** | Decision Support System |
| **Descriptive / Diagnostic / Predictive / Prescriptive** | Chuyện gì đã xảy ra / vì sao / sẽ xảy ra gì / nên làm gì |
| **What-if analysis** | Mô phỏng kết quả theo kịch bản tham số |
| **Data leakage** | Mô hình được thấy trước đáp án (ví dụ dùng `reservation_status`) |
| **AUC, Precision, Recall** | Đánh giá mô hình phân loại (dự đoán hủy) |
| **MAPE** | Sai số phần trăm trung bình (đánh giá dự báo) |
