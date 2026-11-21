## Issue
Closes #<!-- issue number, required: create the issue before starting work -->

## What changed?
<!-- 1–3 sentences: what and why. -->

## How to verify
<!-- Commands to run or pages to open, and what you should see. -->

## Affected components
- [ ] database/ (SQL)
- [ ] etl/
- [ ] ml/
- [ ] backend/
- [ ] frontend/
- [ ] docs/
- [ ] deploy/ / CI

## Checks
- [ ] `ruff check .` and `pytest` pass
- [ ] `npm run lint` and `npm run build` pass (if frontend changed)
- [ ] `python -m etl.run_pipeline` re-runs successfully (if database/ or etl/ changed)
- [ ] Related docs updated (DATA_DICTIONARY, ARCHITECTURE…)
- [ ] No secrets, `.env`, `data/raw/*` or `ml/models/*` committed

## Screenshots (if the UI changed)
