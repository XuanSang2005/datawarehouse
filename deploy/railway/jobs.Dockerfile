# ONE-OFF job on Railway (service "jobs"): ETL pipeline, then train the 2 ML models, writing results to gold.
# The build context is the REPO ROOT (needs etl/, database/, ml/). See deploy/railway/README.md.
FROM python:3.12-slim

WORKDIR /app
COPY etl/requirements.txt etl/requirements.txt
# Install only the ML libraries needed for training (skip jupyter/matplotlib from ml/requirements.txt for a lighter image)
RUN pip install --no-cache-dir -r etl/requirements.txt \
    "scikit-learn>=1.5,<2" "joblib>=1.4,<2"

COPY etl ./etl
COPY database ./database
COPY ml ./ml

# HistGradientBoosting suffers heavy CPU contention on small machines (see ml/README.md)
ENV OMP_NUM_THREADS=2 PYTHONUNBUFFERED=1
CMD ["sh", "-c", "python -m etl.run_pipeline && python -m ml.cancellation.train && python -m ml.forecast.train"]
