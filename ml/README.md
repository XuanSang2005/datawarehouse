# ml/: Phân tích dự đoán

Khám phá dữ liệu và xây mô hình. **Kết quả cho ứng dụng được ghi vào bảng `gold.ml_*`**;
backend chỉ đọc các bảng đó, không train model.

```
ml/
├── notebooks/       Khám phá (EDA), thử nghiệm: NN_<ten>_<chu-de>.ipynb, clear output trước khi commit
├── models/          File model đã train (.joblib), KHÔNG commit
├── tests/           pytest, không cần DB (test_cancellation_*.py, ...)
├── cancellation/    Mô hình dự đoán hủy → gold.ml_booking_risk (E3, xem mục bên dưới)
└── forecast/        (dự kiến) Dự báo nhu cầu tuần → gold.ml_demand_forecast
```

Đọc dữ liệu: dùng `etl.db.connect()` để đọc từ `silver` hoặc `gold`.

## Lưu ý bắt buộc
- ⛔ **Data leakage**: không dùng `reservation_status`, `reservation_status_date`. Cân nhắc bỏ `assigned_room_type`, `booking_changes`, `days_in_waiting_list` (thông tin có thể phát sinh sau thời điểm đặt). Mô hình hủy (E3) đã bỏ cả 5 cột này và `required_car_parking_spaces`: xem mục "Cột bị bỏ và lý do".
- Chia train/test **theo thời gian** (ví dụ train: đến hết 2016, test: 2017), không chia ngẫu nhiên.
- Ghi lại metric dưới đây để đưa vào chương **Evaluation** của báo cáo.

## Mô hình dự đoán hủy (E3): `ml/cancellation/`

```bash
python -m ml.cancellation.train                # train + đánh giá + ghi gold.ml_booking_risk, gold.ml_model_metrics
python -m ml.cancellation.train --no-write     # chỉ train và in metric
pytest ml/tests                                # test chống leakage, chọn ngưỡng (không cần DB)
```
Chạy từ thư mục gốc, DB đã có gold (`python -m etl.run_pipeline`). Mất khoảng 1 phút.
Nếu máy đang chạy việc nặng khác, đặt `OMP_NUM_THREADS=2` để HistGradientBoosting không tranh CPU.

| File | Vai trò |
|---|---|
| `database/ml/20_cancellation_eda.sql` | SELECT cho notebook EDA (silver, có cả cột leakage để chứng minh) |
| `database/ml/21_cancellation_features.sql` | SELECT dữ liệu train/chấm điểm (gold.fact_booking + dimension), KHÔNG có cột leakage |
| `database/ml/02_ml_booking_risk.sql` | DDL `gold.ml_booking_risk` (idempotent, script tự chạy trước khi ghi) |
| `ml/cancellation/features.py` | Danh sách feature, `LEAKAGE_COLUMNS` (cột bị bỏ + lý do), chia tập theo thời gian |
| `ml/cancellation/evaluation.py` | Chọn ngưỡng risk band, metric |
| `ml/cancellation/train.py` | Train 2 mô hình + đối chứng, permutation importance, chấm điểm, ghi DB |
| `ml/cancellation/store.py` | Ghi DB (xóa dòng cùng `model_version` rồi ghi lại, 1 transaction) |
| `ml/notebooks/01_claude_eda_cancellation.ipynb` | EDA: tỉ lệ hủy theo khách sạn, lead time, kênh, cọc, quốc gia, mùa; cột leakage |

Đầu ra: `gold.ml_booking_risk` (119.209 dòng = toàn bộ `gold.fact_booking`, `model_version = cancellation_v1`),
`gold.ml_model_metrics` (100 dòng, `model_name` bắt đầu bằng `cancellation_`), và trong `ml/models/`:
`cancellation_gbm.joblib`, `cancellation_logreg.joblib`, `cancellation_report.json`, `cancellation_feature_importance.csv`.

### Chia tập
- **Train**: arrival_date < 2017-01-01 (78.590 booking). **Test**: năm 2017 (40.619 booking, `is_test_set = TRUE`).
- **Validation** = 6 tháng cuối của train (2016-07 → 2016-12, 29.482 booking): model fit trên phần train trước đó,
  dùng để chọn siêu tham số và ngưỡng risk band. Sau đó fit lại trên toàn bộ train. Tập test không được nhìn khi chọn.
- Điểm của booking trong train (`is_test_set = FALSE`) là điểm **in-sample**, lạc quan hơn thực tế; đánh giá chỉ dựa trên test.

### Feature (29 cột: 13 phân loại + 16 số, tất cả biết được lúc đặt phòng)
| Nhóm | Feature |
|---|---|
| Khách sạn, thời gian | `hotel_name`, `arrival_season` (High/Shoulder/Low), `arrival_day_of_week`, `arrival_is_holiday`, `booking_month` (tháng đặt = tháng của arrival_date − lead_time) |
| Đặt trước, lưu trú, khách | `lead_time`, `weekend_nights`, `week_nights`, `total_nights`, `adults`, `children`, `babies`, `party_type` |
| Kênh | `market_segment`, `distribution_channel`, `agent_id`, `company_id` |
| Khách hàng | `country_code` ⚠, `market_group` ⚠, `customer_type`, `is_repeated_guest`, `previous_cancellations`, `previous_bookings_not_canceled` |
| Booking | `deposit_type`, `meal`, `reserved_room_type`, `adr`, `adr_per_person` (adr / (adults + children)), `total_of_special_requests` |

Category xuất hiện < 100 lần trong train (đại lý, công ty, quốc gia hiếm) được gộp thành nhóm "infrequent".

### Cột bị bỏ và lý do
| Cột | Lý do |
|---|---|
| `reservation_status`, `reservation_status_date` (+ `status_date_key`) | ⛔ Chính là kết quả / ngày hủy |
| `room_nights_sold`, `realized_revenue`, `lost_revenue`, `deposit_retained`, `net_lost_revenue`, `cancel_lead_days` | ⛔ Tính từ `is_canceled` (comment `database/gold/30_fact_booking.sql`) |
| `assigned_room_type` (+ `is_room_changed`) | Gán lúc check-in: booking được đổi phòng chỉ hủy 5,4% (so với 41,6%) |
| `booking_changes` | Tích lũy tới lúc check-in/hủy: booking có sửa hủy 15,7% so với 40,9% |
| `days_in_waiting_list` | Chốt sau ngày nhập booking, không chắc có lúc chấm điểm |
| `required_car_parking_spaces` | 7.416 booking có chỗ đỗ xe (silver) **không booking nào hủy**: nhiều khả năng ghi lúc check-in |
| `arrival_month`, `arrival_week` | Không phải leakage, nhưng mỗi tháng chỉ có 2 năm dữ liệu nên model học thuộc từng năm: AUC validation 0,844 → 0,876 khi bỏ |
| `arrival_date`, năm đến | Chỉ dùng để chia tập; model không ngoại suy được sang năm mới |

`ml/tests/test_cancellation_features.py` khẳng định không cột nào ở trên nằm trong feature set và file
`21_cancellation_features.sql` không chọn cột nào trong số đó.

### Risk band (chọn trên validation)
| Band | Điều kiện | Hành động gợi ý | Test 2017: số booking (tỉ trọng), tỉ lệ hủy thực tế |
|---|---|---|---|
| **High** | p ≥ **0,31** | Đòi cọc / tính vào hạn mức overbooking | 15.988 (39%), hủy 74,1% |
| **Medium** | 0,17 ≤ p < 0,31 | Gọi xác nhận lại, nhắc thanh toán | 6.304 (16%), hủy 35,9% |
| **Low** | p < 0,17 | Không cần can thiệp | 18.327 (45%), hủy 8,9% |

- **High** = ngưỡng nhỏ nhất mà **precision trên validation ≥ 80%**: đòi cọc hay overbooking là hành động tốn kém
  (mất khách, hết phòng) nếu đoán sai, nên cần ít nhất 4/5 booking bị gắn High thực sự hủy.
- **Medium** = ngưỡng làm **F1 lớn nhất** trên validation: lưới rộng cho hành động rẻ (gọi điện), gom ~90% booking hủy.
- Ngưỡng được lưu ở `gold.ml_model_metrics` (`threshold_high`, `threshold_medium`, dataset `validation`)
  để backend hiển thị định nghĩa band.
- Trên test, precision của High là 74% (thấp hơn mục tiêu 80% trên validation): năm 2017 hủy nhiều hơn (38,7% so với
  36,2% ở train). Nên theo dõi và chọn lại ngưỡng khi có dữ liệu mới.

### Feature quan trọng nhất (permutation importance trên test, AUC giảm khi xáo trộn cột)
| # | Feature | AUC giảm |
|---|---|---|
| 1 | `agent_id` | 0,127 |
| 2 | `country_code` | 0,091 |
| 3 | `deposit_type` | 0,080 |
| 4 | `lead_time` | 0,042 |
| 5 | `total_of_special_requests` | 0,040 |
| 6 | `customer_type` | 0,019 |
| 7 | `previous_bookings_not_canceled` | 0,009 |
| 8 | `market_segment` | 0,004 |
| 9 | `previous_cancellations` | 0,003 |
| 10 | `booking_month` | 0,003 |

Lưu ý diễn giải: `deposit_type = Non Refund` hủy 99% vì đó chủ yếu là booking đoàn qua đại lý giữ chỗ rồi hủy;
đây là tương quan, **không** có nghĩa đòi cọc làm khách hủy.

⚠ **Quốc gia**: PRT hủy 57% so với 24% của các nước khác. Quốc tịch có thể chỉ được xác nhận lúc check-in
(booking hủy giữ giá trị mặc định), nếu vậy `country_code` mang một phần kết quả. Model đối chứng bỏ
`country_code` + `market_group` (`cancellation_gbm_no_country`) đạt AUC test **0,843**, thấp hơn mục tiêu 0,85.
Model chính vẫn giữ quốc gia; khi trình bày cần nêu rõ khoảng AUC 0,84–0,89 tùy giả định này.

## Kết quả đánh giá

Tập test: booking đến trong năm 2017 (40.619 booking, tỉ lệ hủy 38,7%). Precision/recall/F1 tại ngưỡng High
của từng model (chọn trên validation). Model chính: `cancellation_gbm`, `model_version = cancellation_v1`.

| Mô hình | Tập test | Metric | Kết quả | Ngày |
|---|---|---|---|---|
| `cancellation_gbm` (HistGradientBoosting, model chính) | 2017 | AUC | **0,888** (train 0,947, validation 0,881) | 2026-11-21 |
| | 2017 | PR-AUC / Brier | 0,843 / 0,138 | 2026-11-21 |
| | 2017 | Ngưỡng High | 0,31 (Medium 0,17) | 2026-11-21 |
| | 2017 | Precision / Recall / F1 (p ≥ 0,31) | 0,741 / 0,752 / 0,747 | 2026-11-21 |
| | 2017 | Precision / Recall / F1 (p ≥ 0,17, Medium + High) | 0,633 / 0,896 / 0,742 | 2026-11-21 |
| | 2017 | Confusion matrix (p ≥ 0,31) | TN 20.740, FP 4.145, FN 3.895, TP 11.839 | 2026-11-21 |
| `cancellation_logreg` (Logistic Regression, baseline) | 2017 | AUC | 0,871 (train 0,913, validation 0,868) | 2026-11-21 |
| | 2017 | PR-AUC / Brier | 0,828 / 0,144 | 2026-11-21 |
| | 2017 | Ngưỡng High | 0,42 (Medium 0,20) | 2026-11-21 |
| | 2017 | Precision / Recall / F1 (p ≥ 0,42) | 0,771 / 0,659 / 0,711 | 2026-11-21 |
| | 2017 | Confusion matrix (p ≥ 0,42) | TN 21.795, FP 3.090, FN 5.359, TP 10.375 | 2026-11-21 |
| `cancellation_gbm_no_country` (đối chứng, bỏ quốc gia) | 2017 | AUC | 0,843 | 2026-11-21 |

Kết luận: model chính đạt mục tiêu G2 (AUC ≥ 0,85). Gradient Boosting hơn baseline 0,016 AUC và có F1 cao hơn.
Cây sâu (63 lá) cho AUC train 0,99 nhưng validation chỉ 0,83 (học thuộc khối booking đoàn trùng lặp), nên model
dùng cây nông (7 lá, tối thiểu 200 mẫu/lá, 400 vòng, learning rate 0,05), chọn theo AUC validation.
