# ml/: Phân tích dự đoán

Khám phá dữ liệu và xây mô hình. **Kết quả cho ứng dụng được ghi vào bảng `gold.ml_*`**;
backend chỉ đọc các bảng đó, không train model.

```
ml/
├── notebooks/       Khám phá (EDA), thử nghiệm: NN_<ten>_<chu-de>.ipynb, clear output trước khi commit
├── models/          File model đã train (.joblib), KHÔNG commit
└── (dự kiến)
    ├── cancellation/    Mô hình dự đoán hủy → gold.ml_booking_risk
    └── forecast/        Dự báo nhu cầu tuần → gold.ml_demand_forecast (đã có, xem mục E4)
```

Đọc dữ liệu: dùng `etl.db.connect()` để đọc từ `silver` hoặc `gold`.

## Lưu ý bắt buộc
- ⛔ **Data leakage**: không dùng `reservation_status`, `reservation_status_date`. Cân nhắc bỏ `assigned_room_type`, `booking_changes`, `days_in_waiting_list` (thông tin có thể phát sinh sau thời điểm đặt).
- Chia train/test **theo thời gian** (ví dụ train: đến hết 2016, test: 2017), không chia ngẫu nhiên.
- Ghi lại metric dưới đây để đưa vào chương **Evaluation** của báo cáo.

## Kết quả đánh giá

| Mô hình | Tập test | Metric | Kết quả | Ngày |
|---|---|---|---|---|
| _chưa có_ | | | | |
| `forecast_gbm` (E4, model chính) | Backtest 2017-01-02 → 2017-08-21, rolling-origin h=1..8 | MAPE (h=1 / h=4 / h=8 / chung) | 6,5% / 7,2% / 11,8% / **8,6%** | 2026-11-21 |
| `forecast_seasonal_naive` (E4, baseline) | như trên | MAPE (h=1 / h=4 / h=8 / chung) | 11,6% / 11,6% / 11,6% / 11,6% | 2026-11-21 |
| `forecast_moving_avg` (E4, baseline MA 4 tuần) | như trên | MAPE (h=1 / h=4 / h=8 / chung) | 6,5% / 10,0% / 19,5% / 11,8% | 2026-11-21 |
| `forecast_gbm` (E4) | như trên | Độ phủ khoảng 80% | 85,7% (seasonal naive 76,5%, MA 63,6%) | 2026-11-21 |

## E4: Dự báo nhu cầu theo tuần

Dự báo **room-nights bán được** (đêm phòng của booking không hủy) theo khách sạn × tuần, phục vụ trang
"Dự báo nhu cầu". Code: `ml/forecast/`; SQL: `database/ml/03_ml_demand_forecast.sql` (DDL),
`database/ml/31_forecast_weekly_series.sql` (SELECT chuỗi tuần).

```bash
python -m ml.forecast.train            # backtest + dự báo tương lai + ghi DB (~1–3 phút)
python -m ml.forecast.train --dry-run  # chỉ in bảng metric, không ghi DB
pytest ml/tests                        # unit test (không cần DB)
```

Script chạy lại được nhiều lần: xóa dòng có `model_version` / `model_name` của chính nó (`forecast_*`) rồi ghi lại,
không đụng dòng của E3 trong `gold.ml_model_metrics`.

### Dữ liệu
- Nguồn: `gold.fact_daily_occupancy` (tổng `rooms_occupied`) gộp theo `gold.dim_date.week_start_date` (Thứ Hai).
- **Tuần biên thiếu ngày bị loại**: 2015-06-29 (chỉ 5 đêm, từ 01/07) và 2017-08-28 (chỉ 4 đêm, đến 31/08).
  Tổng của chúng thấp giả tạo nên không dùng để train cũng như làm actual; tuần 2017-08-28 được coi là
  tuần tương lai đầu tiên (`actual_room_nights` = NULL). Còn lại **112 tuần đủ 7 đêm/khách sạn**
  (2015-07-06 → 2017-08-21), liên tục không hở.
- "Cùng tuần năm trước" = lùi 52 tuần (364 ngày, cùng thứ). Năm ISO 2015 có 53 tuần nên lệch tối đa 1 tuần
  so với số tuần ISO; chấp nhận được.

### Mô hình
| Model | Cách dự báo tuần origin+h |
|---|---|
| `forecast_seasonal_naive` | Giá trị cùng tuần năm trước (t − 52) |
| `forecast_moving_avg` | Trung bình 4 tuần gần nhất, giữ phẳng cho mọi h |
| `forecast_gbm` | `HistGradientBoostingRegressor` (scikit-learn) gộp 2 khách sạn, dự báo **đệ quy** (dự báo h=1 làm lag cho h=2…). Feature: `is_resort`, `iso_week`, `n_holidays` (số ngày lễ trong tuần, `dim_date.is_holiday`), `lag_1`, `lag_2`, `ma_4`, `lag_52`, `seasonal_3` (TB tuần t−51..t−53), `yoy_level` (ma_4 / ma_4 cùng kỳ năm trước), `seasonal_adj` = `seasonal_3 × yoy_level`. Siêu tham số chọn trước (depth 3, 300 vòng, lr 0.05), chỉ so thử 3 cấu hình trên cửa sổ calibration (chênh < 0,3 điểm MAPE), không tinh chỉnh trên tập test |

Không dùng SARIMA/Prophet: chỉ có 2 chu kỳ năm (~112 tuần), mô hình mùa vụ 52 tuần ước lượng rất bất ổn;
GBM dùng được `lag_52` như một feature thường và gộp 2 khách sạn để có gấp đôi mẫu. Không thêm thư viện mới.

### Đánh giá: backtest rolling-origin
- Ở **mỗi tuần gốc** (origin), cắt dữ liệu đến origin, học lại model, dự báo h = 1..8 tuần. Mỗi tuần mục tiêu có
  đúng 1 dự báo cho mỗi h. Không có thông tin sau origin lọt vào feature (lag ≥ 52 luôn là số thật khi h ≤ 8).
- **Cửa sổ calibration**: tuần mục tiêu 2016-07-04 → 2016-12-26. Dùng để ước lượng khoảng dự báo.
- **Cửa sổ test**: tuần mục tiêu 2017-01-02 → 2017-08-21 (34 tuần × 2 khách sạn × 8 horizon). MAPE báo cáo ở đây.
- MAPE = trung bình |actual − dự báo| / actual, lưu dạng tỉ lệ trong `gold.ml_model_metrics` (`dataset = 'backtest'`;
  `'calibration'` cho cửa sổ 2016).

| MAPE test 2017 | GBM | Seasonal naive | Moving avg |
|---|---|---|---|
| Chung (h=1..8, 2 khách sạn) | **8,6%** | 11,6% | 11,8% |
| h=1 City Hotel | 6,7% | 12,2% | **6,6%** |
| h=1 Resort Hotel | **6,2%** | 10,9% | 6,4% |
| h=1..8 City Hotel | **8,4%** | 12,2% | 11,4% |
| h=1..8 Resort Hotel | **8,8%** | 10,9% | 12,2% |
| h=4 | **7,2%** | 11,6% | 10,0% |
| h=8 | 11,8% | **11,6%** | 19,5% |
| Cửa sổ calibration 2016-H2, chung | **12,0%** | 24,9% | 18,2% |

Nhận xét:
- GBM thắng cả 2 baseline ở MAPE chung (8,6% so với 11,6%/11,8%) và ở mọi horizon 2–7 tuần.
- h=1: GBM ngang moving average (6,5% vs 6,5%): tuần kế tiếp gần như bằng mức 4 tuần gần nhất, khó hơn được.
- h=8: GBM ngang seasonal naive (11,8% vs 11,6%): khi dự báo xa, thông tin mùa vụ năm trước chiếm ưu thế,
  còn sai số đệ quy của GBM tích lũy.
- Seasonal naive tệ ở 2016 (24,9%) vì City Hotel 07–08/2015 thấp bất thường (~150–1.000 room-nights/tuần, so
  với ~1.500 năm 2016) — dữ liệu City Hotel mới "lên" dần từ 2015.

### Khoảng dự báo (lower/upper)
Khoảng 80% thực nghiệm: theo từng h, lấy phân vị 10% và 90% của sai số tương đối `actual / dự báo − 1`
(gộp 2 khách sạn) → `lower = dự báo × (1 + q10)`, `upper = dự báo × (1 + q90)`.
- Tuần test 2017: phân vị lấy từ cửa sổ calibration 2016 (không nhìn trước test). Độ phủ thực tế trên test:
  GBM 85,7%, seasonal naive 76,5%, moving average 63,6%.
- 8 tuần tương lai: phân vị lấy từ toàn bộ sai số backtest (calibration + test), vì đều đã biết tại thời điểm dự báo.
- Khoảng **lệch lên** (upper xa hơn lower) vì ở 2016 model hay dự báo thấp khi nhu cầu City Hotel tăng mạnh so
  với 2015. Upper có thể vượt công suất thực của khách sạn (dataset không có số phòng, quy tắc 10).

### Hạn chế
- Chỉ ~2 năm dữ liệu: mới có 1 năm để học quan hệ "cùng kỳ năm trước"; các origin đầu cửa sổ calibration
  (trước 07/2016) chưa có `lag_52` nên model chỉ dựa vào mức gần đây và tuần trong năm.
- Ở cao điểm hè cả 2 khách sạn gần như **kín phòng** (Resort ~1.270, City ~1.540 room-nights/tuần): nhu cầu thật
  bị cắt trần bởi công suất, model dự báo room-nights bán được chứ không phải nhu cầu không ràng buộc.
- Room-nights tính theo booking không hủy **cuối cùng** (biết sau khi khách ở), nên dự báo trả lời "sẽ bán được
  bao nhiêu đêm phòng", không phải "on-the-books tại thời điểm dự báo" (dataset không có snapshot theo ngày đặt).
- 2 khách sạn, 1 quốc gia: `n_holidays` ít biến thiên (≤ 13 ngày lễ/năm), đóng góp nhỏ.
- 8 tuần tương lai (2017-08-28 → 2017-10-16) không thể kiểm chứng vì dataset kết thúc 2017-08-31.
