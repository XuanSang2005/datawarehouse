# Deploy lên Railway

Bản online để demo. Mỗi thành phần là một service của Railway, deploy bằng Railway CLI từ máy có repo
(không cần GitHub integration). Cấu hình docker compose ở máy local **không đổi**: các biến mới đều có mặc định.

| Service | Nguồn | Vai trò |
|---|---|---|
| `Postgres` | Database của Railway | Lakehouse (bronze/silver/gold/meta) |
| `jobs` | `deploy/railway/jobs.Dockerfile` (context = gốc repo) | Chạy **một lần**: `etl.run_pipeline` → `ml.cancellation.train` → `ml.forecast.train`, rồi thoát |
| `backend` | `backend/Dockerfile` | FastAPI, lắng nghe `$PORT` do Railway cấp |
| `frontend` | `frontend/Dockerfile` | nginx phục vụ bản build React, proxy `/api/*` sang `BACKEND_URL` |

## Biến môi trường

`backend` và `jobs` (tham chiếu biến của service Postgres, Railway tự điền):
```
POSTGRES_HOST=${{Postgres.PGHOST}}
POSTGRES_PORT=${{Postgres.PGPORT}}
POSTGRES_USER=${{Postgres.PGUSER}}
POSTGRES_PASSWORD=${{Postgres.PGPASSWORD}}
POSTGRES_DB=${{Postgres.PGDATABASE}}
```
`jobs` thêm `RAILWAY_DOCKERFILE_PATH=deploy/railway/jobs.Dockerfile`.

`frontend`: `BACKEND_URL=https://<domain công khai của backend>` (vd `https://backend-production-xxxx.up.railway.app`).
`PORT` do Railway tự đặt cho mọi service.

## Các bước (Railway CLI ≥ 4)

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
Deploy job dữ liệu (từ gốc repo) và backend:
```bash
railway up --service jobs --detach
```
```bash
railway up backend --path-as-root --service backend --detach
```
```bash
railway domain --service backend
```
Đợi `jobs` chạy xong (trạng thái deployment `SUCCESS`, log có dòng "Pipeline hoàn tất" và 2 lần ghi bảng ML):
```bash
railway deployment list --service jobs
```
Tạo frontend, trỏ vào domain backend vừa tạo, rồi deploy:
```bash
railway add --service frontend --variables 'BACKEND_URL=https://<domain-backend>'
```
```bash
railway up frontend --path-as-root --service frontend --detach
```
```bash
railway domain --service frontend
```

## Gói Free: tối đa 3 service

Postgres + backend + jobs đã đủ 3, nên sau khi `jobs` chạy xong thì **xóa service `jobs`** (dữ liệu vẫn nằm trong
Postgres) rồi mới tạo `frontend`. Muốn chạy lại pipeline/ML sau này: xóa tạm `frontend`, tạo lại `jobs` theo
lệnh trên, chạy xong thì xóa `jobs` và tạo lại `frontend`. Gói trả phí không có giới hạn này: giữ `jobs` và bấm
Redeploy khi cần chạy lại.

## Kiểm tra
- `https://<domain-backend>/api/health` → `{"status": "ok", "database": "up", ...}`
- `https://<domain-frontend>/` mở được 6 trang; trang Pipeline hiện lần chạy ETL trên Railway.
