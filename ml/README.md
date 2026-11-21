# ml/: Phân tích dự đoán

Khám phá dữ liệu và xây mô hình. **Kết quả cho ứng dụng được ghi vào bảng `gold.ml_*`**;
backend chỉ đọc các bảng đó, không train model.

```
ml/
├── notebooks/       Khám phá (EDA), thử nghiệm: NN_<ten>_<chu-de>.ipynb, clear output trước khi commit
├── models/          File model đã train (.joblib), KHÔNG commit
└── (dự kiến)
    ├── cancellation/    Mô hình dự đoán hủy → gold.ml_booking_risk
    └── forecast/        Dự báo nhu cầu tuần → gold.ml_demand_forecast
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
