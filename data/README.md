# data/

| Thư mục | Nội dung | Commit? |
|---|---|---|
| `raw/` | File nguồn do `python -m etl.run_pipeline` (bước extract) tải hoặc sinh ra | ❌ Không |

Không sửa tay file trong `raw/`. Muốn tải lại thì chạy `python -m etl.run_pipeline --refresh-sources`.
