# Image that runs the ETL pipeline once (service `etl` in docker-compose.yml).
# The build context is the REPO ROOT because the pipeline needs both etl/ and database/.
FROM python:3.12-slim

WORKDIR /app
COPY etl/requirements.txt etl/requirements.txt
RUN pip install --no-cache-dir -r etl/requirements.txt

COPY etl ./etl
COPY database ./database

CMD ["python", "-m", "etl.run_pipeline"]
