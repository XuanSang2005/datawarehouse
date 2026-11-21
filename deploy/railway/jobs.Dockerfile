# Job chạy MỘT LẦN trên Railway (service "jobs"): pipeline ETL rồi train 2 model ML, ghi kết quả vào gold.
# Build context là THƯ MỤC GỐC repo (cần etl/, database/, ml/). Xem deploy/railway/README.md.
FROM python:3.12-slim

WORKDIR /app
COPY etl/requirements.txt etl/requirements.txt
# Chỉ cài thư viện ML cần để train (bỏ jupyter/matplotlib của ml/requirements.txt cho image nhẹ)
RUN pip install --no-cache-dir -r etl/requirements.txt \
    "scikit-learn>=1.5,<2" "joblib>=1.4,<2"

COPY etl ./etl
COPY database ./database
COPY ml ./ml

# HistGradientBoosting tranh CPU rất nặng khi máy chật (xem ml/README.md)
ENV OMP_NUM_THREADS=2 PYTHONUNBUFFERED=1
CMD ["sh", "-c", "python -m etl.run_pipeline && python -m ml.cancellation.train && python -m ml.forecast.train"]
