# Image chạy pipeline ETL một lần (service `etl` trong docker-compose.yml).
# Build context là THƯ MỤC GỐC repo vì pipeline cần cả etl/ lẫn database/.
FROM python:3.12-slim

WORKDIR /app
COPY etl/requirements.txt etl/requirements.txt
RUN pip install --no-cache-dir -r etl/requirements.txt

COPY etl ./etl
COPY database ./database

CMD ["python", "-m", "etl.run_pipeline"]
