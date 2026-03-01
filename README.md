# Smart Expense Tracker

Phase 1 scaffolding completed for:
- FastAPI backend
- PostgreSQL + pgvector (via Docker Compose)
- SQLAlchemy + Alembic migration baseline
- React frontend (Vite)

## 1) Start PostgreSQL + pgvector

```powershell
docker compose up -d db
```

PostgreSQL is exposed on `localhost:55432` to avoid conflicts with local PostgreSQL services.

## 2) Backend setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Backend API: http://localhost:8000
Health endpoint: http://localhost:8000/api/v1/health

## 3) Frontend setup

```powershell
cd frontend
npm install
npm run dev
```

Frontend app: http://localhost:5173

Optional frontend env:

- `VITE_API_BASE_URL` (default: `http://localhost:8000/api/v1`)

## Phase 1 Notes

- Auth, expenses, budgets, and analytics endpoints are available in the backend.
- AI chat endpoint is available at `POST /api/v1/ai/chat` (requires `LLM_API_KEY` in backend `.env`).
- RAG embedding refresh endpoint is available at `POST /api/v1/ai/embeddings/rebuild`.
- n8n automation endpoints are available under `/api/v1/automation/*` with `X-Automation-Key` header.
- Frontend Phase 6 pages are implemented: Login/Register, Dashboard, Expenses, Budgets, and AI Chat.
