# Deploying to Railway

Online version for the demo. Each component is a Railway service, deployed with the Railway CLI from a machine with the repo
(no GitHub integration needed). The local docker compose setup is **unchanged**: all new variables have defaults.

| Service | Source | Role |
|---|---|---|
| `Postgres` | Railway database | Lakehouse (bronze/silver/gold/meta) |
| `jobs` | `deploy/railway/jobs.Dockerfile` (context = repo root) | Runs **once**: `etl.run_pipeline` → `ml.cancellation.train` → `ml.forecast.train`, then exits |
| `backend` | `backend/Dockerfile` | FastAPI, listening on the `$PORT` provided by Railway |
| `frontend` | `frontend/Dockerfile` | nginx serving the React build, proxying `/api/*` to `BACKEND_URL` |

## Environment variables

`backend` and `jobs` (references to the Postgres service variables, filled in by Railway):
```
POSTGRES_HOST=${{Postgres.PGHOST}}
POSTGRES_PORT=${{Postgres.PGPORT}}
POSTGRES_USER=${{Postgres.PGUSER}}
POSTGRES_PASSWORD=${{Postgres.PGPASSWORD}}
POSTGRES_DB=${{Postgres.PGDATABASE}}
```
`jobs` also sets `RAILWAY_DOCKERFILE_PATH=deploy/railway/jobs.Dockerfile`.

`frontend`: `BACKEND_URL=https://<public backend domain>` (e.g. `https://backend-production-xxxx.up.railway.app`).
`PORT` is set by Railway for every service.

## Steps (Railway CLI ≥ 4)

```bash
npm install -g @railway/cli
```
```bash
railway login
```
```bash
railway init --name tourism-dss
```
```bash
railway add --database postgres
```
```bash
railway add --service backend --variables 'POSTGRES_HOST=${{Postgres.PGHOST}}' --variables 'POSTGRES_PORT=${{Postgres.PGPORT}}' --variables 'POSTGRES_USER=${{Postgres.PGUSER}}' --variables 'POSTGRES_PASSWORD=${{Postgres.PGPASSWORD}}' --variables 'POSTGRES_DB=${{Postgres.PGDATABASE}}'
```
```bash
railway add --service jobs --variables 'POSTGRES_HOST=${{Postgres.PGHOST}}' --variables 'POSTGRES_PORT=${{Postgres.PGPORT}}' --variables 'POSTGRES_USER=${{Postgres.PGUSER}}' --variables 'POSTGRES_PASSWORD=${{Postgres.PGPASSWORD}}' --variables 'POSTGRES_DB=${{Postgres.PGDATABASE}}' --variables 'RAILWAY_DOCKERFILE_PATH=deploy/railway/jobs.Dockerfile'
```
Deploy the data job (from the repo root) and the backend:
```bash
railway up --service jobs --detach
```
```bash
railway up backend --path-as-root --service backend --detach
```
```bash
railway domain --service backend
```
Wait for `jobs` to finish (deployment status `SUCCESS`, the log shows "Pipeline finished" and 2 ML table writes):
```bash
railway deployment list --service jobs
```
Create the frontend, pointing at the backend domain just created, then deploy:
```bash
railway add --service frontend --variables 'BACKEND_URL=https://<backend-domain>'
```
```bash
railway up frontend --path-as-root --service frontend --detach
```
```bash
railway domain --service frontend
```

## Free plan: at most 3 services

Postgres + backend + jobs already make 3, so once `jobs` has finished, **delete the `jobs` service** (the data stays in
Postgres) before creating `frontend`. To re-run the pipeline/ML later: temporarily delete `frontend`, recreate `jobs` with
the command above, and when it finishes delete `jobs` and recreate `frontend`. Paid plans have no such limit: keep `jobs` and
click Redeploy when you need to re-run it.

## Verification
- `https://<backend-domain>/api/health` → `{"status": "ok", "database": "up", ...}`
- `https://<frontend-domain>/` opens all 6 pages; the Pipeline page shows the ETL run on Railway.
