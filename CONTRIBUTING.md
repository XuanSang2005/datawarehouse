# Contributing guide (CONTRIBUTING)

The team's shared workflow. Read it all **once** before writing code.

---

## 1. Ownership by component

Each directory has **one main owner**. The owner reviews PRs that touch that directory.
Anyone may change anything, but the owner must approve.

| Directory | Main owner | Support |
|---|---|---|
| `database/` (bronze/silver/gold, checks) | _TBD_ | |
| `etl/` | _TBD_ | |
| `ml/` | _TBD_ | |
| `backend/` | _TBD_ | |
| `frontend/` | _TBD_ | |
| `docs/`, `deliverables/` (report, slides, video) | _Whole team_ | |

> The assignment requires a contribution report for each member (Appendix 1. Teamwork report). Clear commits and PRs are the evidence.

---

## 2. Git workflow

### Branches
- `main`: always runnable. **No direct pushes**; merge only through Pull Requests.
- Working branches are created from `main` and named `<type>/<directory>-<short-description>`:

| Example | When |
|---|---|
| `feat/gold-dim-date` | New feature |
| `fix/etl-header-mismatch` | Bug fix |
| `docs/report-chapter-3` | Documentation, report |
| `refactor/backend-kpi-service` | Code restructuring without behavior change |

### Commits: follow [Conventional Commits](https://www.conventionalcommits.org/)
```
<type>(<scope>): <short description, present tense>
```
- **type**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
- **scope**: directory or layer name: `database`, `bronze`, `silver`, `gold`, `checks`, `etl`, `ml`, `backend`, `frontend`, `docs`

Examples:
```
feat(gold): add fact_booking with surrogate keys
fix(silver): handle 'NA' in children column
feat(frontend): add KPI cards to overview page
docs(report): write chapter 2 business problem
```

### Steps for a piece of work
**Step 0: create an issue before coding** (mandatory, see rule 11 in `CLAUDE.md`).
On GitHub: **Issues → New issue** tab; write the context, what to do and the acceptance criteria (checklist).
Note the issue number (e.g. `#12`) to link it to the PR.

```bash
git checkout main && git pull
```
```bash
git checkout -b feat/gold-dim-date
```
Write code, then commit small and often:
```bash
git add database/gold/10_dim_date.sql && git commit -m "feat(gold): add dim_date"
```
```bash
git push -u origin feat/gold-dim-date
```
Then open a Pull Request on GitHub, fill in the template (write `Closes #12` so the issue closes automatically on merge), and ask the owner for a review.

### Pull Requests
- Every PR must link **one issue** (`Closes #..` in the description). No issue, no merge.
- One PR does **one thing**, ideally under about 400 changed lines.
- It must pass a **green CI** (lint, tests, pipeline run, frontend build).
- At least **1 approval** before merging. Use **Squash and merge**.
- For UI changes, attach screenshots.

---

## 3. Conventions per component

### Language
- Documentation, code comments, commit messages, PR descriptions and UI text are in **English**.
- Names of variables, tables and columns are in English: `snake_case` (Python/SQL), `camelCase` (TS).

### 🗄️ `database/`: SQL
- **File name**: `NN_table_name.sql` (2 digits, lowercase, underscores). The pipeline runs files in **file-name order**.
- **Idempotent**: rerunning does not fail. Full-load tables use `DROP TABLE IF EXISTS` followed by `CREATE TABLE`.
- **Mandatory header** at the top of each file: table name, source, **grain**, main transformations (see `database/silver/01_hotel_bookings.sql`).
- Numbering in gold: `1x` = dimension, `3x` = fact, `5x` = KPI/view.
- Naming: tables `dim_*`, `fact_*`, `kpi_*`, `ml_*`; surrogate keys `<dim>_key`; flag columns `is_*`; dates `*_date`.
- Check files: first line `-- severity: error|warning`; the SELECT returns the **violating rows**.
- After changes: run `python -m etl.run_pipeline --from <layer>` and update `docs/DATA_DICTIONARY.md`.

### ⚙️ `etl/`: Python pipeline
- Do not write data transformation logic in pandas here. Transformations are done in SQL in `database/`.
  `etl/` only **downloads, loads and orchestrates**.
- Adding a new source:
  1. Write `etl/extract/<source_name>.py` with a function `extract(target: Path)`
  2. Write the DDL `database/bronze/NN_<source_name>.sql` (TEXT columns, matching the CSV header)
  3. Register it in `SOURCES` in `etl/extract/__init__.py`
- Log with `logging.getLogger("etl.<module>")`, not `print`.

### 🤖 `ml/`
- Notebooks are named `NN_<name>_<topic>.ipynb`, e.g. `01_an_eda-cancellation.ipynb`. **Clear outputs before committing.**
- Reusable code and the official training code go into `.py` files in `ml/`, not in notebooks.
- Results for the application are **written to `gold.ml_*` tables**. The backend only reads those tables.
- Record the evaluation metrics (AUC, MAPE…) in `ml/README.md` so they can go into the Evaluation chapter.

### 🔌 `backend/`
To add an endpoint, in this order:
1. `app/schemas/<topic>.py`: Pydantic model for the response
2. `app/repositories/<topic>_repo.py`: SQL queries (read only `gold`/`meta`)
3. `app/services/<topic>_service.py`: logic, calculations
4. `app/api/routes/<topic>.py`: HTTP endpoint, then include it in `app/api/router.py`
5. `tests/test_<topic>.py`

Routes **contain no SQL**; repositories **contain no business logic**.

### 🖥️ `frontend/`
To add a page:
1. `src/types/api.ts`: add a type matching the backend schema
2. `src/api/endpoints.ts`: add the API call function
3. `src/pages/<Name>Page.tsx`: the page, using the `useApi` hook
4. `src/routes.tsx`: add 1 line (the sidebar updates automatically)

- Reusable components go in `src/components/` (`common/`, `charts/`, `filters/`, `layout/`).
- Component file names: `PascalCase.tsx`; hooks: `useXxx.ts`.
- Never call `fetch` directly in a component.

---

## 4. Before pushing
```bash
ruff check . && pytest
```
```bash
cd frontend && npm run lint && npm run build
```
If you changed `database/` or `etl/`:
```bash
python -m etl.run_pipeline
```

## 5. General rules
- Do not commit `.env`, data (`data/raw/`), models (`ml/models/`), or videos.
- Do not commit passwords or API keys in code.
- When you hit an error: check `docs/TROUBLESHOOTING.md` first, then ask the team with the **full error log** and the **command you ran**.
