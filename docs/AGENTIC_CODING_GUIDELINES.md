# AGENTIC CODING GUIDELINES

## 1) Purpose

These guidelines define how to safely and consistently build, run, test, and deploy the Smart Expense Tracker using an agentic workflow.

Goals:

- Keep changes small, testable, and reversible.
- Prefer root-cause fixes over temporary patches.
- Preserve production reliability (Render) and local reproducibility (Docker + `.env`).
- Maintain secure handling of credentials and API keys.

---

## 2) Core Engineering Principles

- Make the smallest possible change that solves the real issue.
- Keep backend and frontend contracts synchronized (`/api/v1`, payload shapes, auth flows).
- Validate assumptions with logs, endpoint checks, and targeted tests.
- Fail fast on startup for infra-critical steps (migrations must succeed before app boot).
- Do not hardcode secrets or environment-specific URLs in source code.

---

## 3) Repository Structure (high-level)

- `backend/` — FastAPI, SQLAlchemy, Alembic, auth, analytics, AI, automation endpoints.
- `frontend/` — React + Vite SPA.
- `docs/n8n/` — importable automation workflow JSONs and usage docs.
- `render.yaml` — Render Blueprint for managed deployment.
- `docker-compose.yml` — local Postgres/pgvector and n8n services.

---

## 4) Environment & Secrets Policy

Use environment variables for all sensitive or deployment-specific config.

Required backend envs (minimum):

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `AUTOMATION_API_KEY`
- `CORS_ORIGINS`
- `LLM_API_KEY` (if AI features enabled)

Frontend env:

- `VITE_API_BASE_URL` (must include `/api/v1`)

Rules:

- Never commit real keys to Git.
- If a secret was ever exposed, rotate it immediately.
- On Render Blueprint, prefer linked values (`fromDatabase`) over manual overrides.

---

## 5) Local Development Setup

## 5.1 Python + Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Health check:

- `http://localhost:8000/api/v1/health`

## 5.2 Frontend (React + Vite)

```powershell
cd frontend
npm install
npm run dev
```

Default local app URL:

- `http://localhost:5173`

---

## 6) PostgreSQL + pgvector (Docker)

Start local DB:

```powershell
docker compose up -d db
```

Guidelines:

- Keep local DB port/config consistent with backend `.env`.
- Run Alembic migrations after schema changes.
- Use transactional migrations and avoid destructive edits without backups.

---

## 7) n8n Automation Guidelines

Start n8n locally:

```powershell
docker compose up -d n8n
```

Open n8n:

- `http://localhost:5678`

Workflow standards:

- Keep workflow JSONs in `docs/n8n/`.
- Use explicit webhook method (`POST`) and stable payload mapping.
- Ensure backend automation endpoints include required `X-Automation-Key`.
- Validate end-to-end by confirming records appear through backend APIs.

---

## 8) MCP (Model Context Protocol) Guidelines

For MCP-enabled features:

- Keep MCP logic isolated from core business logic.
- Log tool invocations in a structured format (serializable fields only).
- Handle tool failures gracefully with clear user-safe errors.
- Version prompt/tool schemas when making breaking changes.

Operational checks:

- Verify MCP routes are reachable under `/api/v1`.
- Confirm auth and authorization behavior for each tool-exposed action.

---

## 9) RAG (Retrieval Augmented Generation) Guidelines

RAG principles:

- Separate ingestion/indexing from query serving.
- Keep embedding model and retrieval `top_k` configurable via env.
- Rebuild embeddings after major data shape changes.
- Return grounded answers; prefer retrieval evidence over model guesswork.

Validation checklist:

- Embedding rebuild endpoint succeeds.
- Retrieval returns relevant chunks for known queries.
- Chat endpoint handles missing `LLM_API_KEY` gracefully.

---

## 10) API & Auth Contract Rules

- API base prefix is `/api/v1`.
- Auth endpoints are POST-only (`/auth/register`, `/auth/login`).
- Do not interpret `GET /auth/login` 405 as an outage; only POST matters.
- Keep request/response schemas typed and validated (UUIDs, dates, numbers).

---

## 11) CORS Rules (Critical)

Backend `CORS_ORIGINS` must list frontend origin(s) only, comma-separated.

Example:

- `https://smart-expense-frontend-a5km.onrender.com`

Important:

- No trailing slash.
- `VITE_API_BASE_URL` points to backend; `CORS_ORIGINS` lists frontend.
- If frontend domain changes, update CORS and redeploy backend.

---

## 12) Render Deployment Guidelines

Blueprint source:

- `render.yaml`

Current deployment model:

- Managed Render Postgres via top-level `databases:`.
- Backend `DATABASE_URL` linked from `fromDatabase.connectionString`.

Rules:

- Do not manually set `DATABASE_URL` to empty string or HTTP URL.
- Avoid manual override when Blueprint-linked value exists.
- Backend start command must fail fast if migration fails:
  - `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

After env changes:

- Redeploy backend for backend env changes.
- Redeploy frontend for any `VITE_*` changes (build-time variables).

---

## 13) Testing & Validation Workflow

Backend tests:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q
```

Expected baseline: all tests pass before pushing deployment changes.

Minimum validation before merge/deploy:

- `GET /api/v1/health` returns 200.
- Auth register/login works from frontend and direct API call.
- Expense CRUD and dashboard analytics endpoints respond correctly.
- Automation webhook path tested at least once end-to-end.

---

## 14) Troubleshooting Playbook

1. `Backend unreachable` in UI

- Check frontend `VITE_API_BASE_URL` includes correct backend host + `/api/v1`.
- Check browser Network request URL actually matches expected host.

2. CORS errors

- Verify backend `CORS_ORIGINS` includes exact frontend origin.
- Confirm no trailing slash and redeploy backend.

3. Deploy fails on DB URL

- Ensure `DATABASE_URL` is not blank and not manually malformed.
- Prefer Blueprint-linked DB value.

4. Auth endpoint confusion

- `GET /auth/login` => 405 is normal.
- Validate `POST /api/v1/auth/login` behavior.

---

## 15) Git & Change Management

- Use focused commits with clear prefixes (`fix:`, `deploy:`, `docs:`).
- Keep infra changes (`render.yaml`, env contracts) explicit in commit messages.
- Push only after tests pass or risk is explicitly acknowledged.

---

## 16) Definition of Done (Agentic)

A task is done when:

- Code changes are minimal and correct.
- Relevant tests pass.
- Runtime behavior validated (local or deployed as applicable).
- Docs/env instructions updated when behavior or deployment contracts change.
- No secrets introduced into tracked files.
