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
- `EMBEDDING_MODEL`, `RAG_TOP_K` (RAG tuning; have working defaults, no MCP-specific env vars needed -- the MCP server reuses `JWT_SECRET_KEY`)

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

Two distinct layers, both wrapping the same deterministic service functions
via `app/mcp/tools.py::execute_tool` -- don't duplicate business logic
between them:

- `app/mcp/tools.py` -- OpenAI-style function-calling schemas for the
  in-process AI chat loop (`app/ai/orchestrator.py`). Reachable only
  indirectly, through `POST /api/v1/ai/chat`.
- `app/mcp/server.py` -- the real Model Context Protocol server, mounted at
  `/mcp` (top-level, not under `/api/v1`), for external MCP clients.

For MCP-enabled features:

- Keep MCP logic isolated from core business logic.
- Log tool invocations in a structured format (serializable fields only) --
  external MCP calls are tagged `mcp:<tool_name>` in the tool-call log to
  distinguish them from in-app chat tool calls.
- Handle tool failures gracefully with clear user-safe errors (raise
  `mcp.server.mcpserver.exceptions.ToolError` in `app/mcp/server.py` tools,
  not a bare exception, so the client gets the message instead of a stack
  trace).
- Version prompt/tool schemas when making breaking changes.

Operational checks:

- Verify the in-app tool-calling path works end-to-end via `POST /api/v1/ai/chat`.
- Verify the real MCP server is reachable at `/mcp` and rejects calls without a valid `Authorization: Bearer <token>`.
- Confirm auth and authorization behavior for each tool-exposed action -- every MCP tool call must resolve to, and act only on, the JWT's own user.

---

## 9) RAG (Retrieval Augmented Generation) Guidelines

RAG principles:

- Separate ingestion/indexing (`app/rag/service.py`) from query serving (`retrieve_context`, called from `app/ai/orchestrator.py`).
- Keep embedding model and retrieval `top_k` configurable via env (`EMBEDDING_MODEL`, `RAG_TOP_K`).
- Sync embeddings at write time, not on a schedule: every expense create/update/delete calls `sync_expense_related_embeddings` / `sync_expense_deletion`, which upsert three granularities (per-expense, daily-summary, monthly-summary) keyed by a dedup `metadata.key`. Don't add a new periodic-rebuild trigger without a reason -- write-time sync already keeps things current.
- Embedding sync must never block expense CRUD: catch `RAGError` at the sync boundary (see existing pattern), don't let it propagate.
- Return grounded answers; prefer retrieval evidence over model guesswork.

Maintenance endpoints (for gaps write-time sync can't cover):

- `POST /api/v1/ai/embeddings/backfill` -- rebuilds all three granularities from a user's full history. Use once when enabling RAG on pre-existing data.
- `POST /api/v1/automation/embeddings/daily-rebuild` -- automation-key gated, re-syncs one day. Wired to n8n's nightly schedule (`docs/n8n/daily_embedding_rebuild_workflow.json`) as a safety net for sync failures, not the primary mechanism.
- `POST /api/v1/ai/embeddings/rebuild` -- manual single-month rebuild (legacy manual control, still works).

Validation checklist:

- Adding/editing/deleting an expense updates the corresponding rows in the `embeddings` table (check via `metadata.key`), without leaving stale duplicates.
- Retrieval returns relevant chunks for known queries.
- Chat endpoint handles missing `LLM_API_KEY` gracefully.
- Embeddings API failures (bad key, provider down) don't return an error from expense CRUD endpoints.

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
- Migrations run as `preDeployCommand` (`alembic upgrade head`), separate from `startCommand` (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`). This is deliberate: a failed migration blocks the new deploy without taking down an already-running instance, unlike chaining `alembic upgrade head && uvicorn ...` into `startCommand`. Don't recombine them.
- If a deploy fails with `psycopg.OperationalError: ... Name or service not known`, that's DNS resolution failing on the DB host -- check first whether the free-tier Postgres database expired (Render deletes free databases 30 days after creation), then whether `DATABASE_URL` was manually overridden, then region match between backend and DB services.

After env changes:

- Redeploy backend for backend env changes.
- Redeploy frontend for any `VITE_*` changes (build-time variables).

---

## 13) Testing & Validation Workflow

Backend tests:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Frontend tests:

```powershell
cd frontend
npm test
```

Both run automatically in CI (`.github/workflows/ci.yml`) on every push/PR. Expected baseline: all tests pass before pushing deployment changes.

Backend tests use mocked DB sessions and mocked HTTP/embedding calls throughout (see `tests/`) -- there is no real Postgres or real LLM key in CI. That means passing tests confirm the logic layer, not that a live embeddings call or live pgvector query actually works end to end. Validate those manually against a local `docker compose up -d db` + real `LLM_API_KEY` before trusting RAG/AI behavior in a deploy.

Minimum validation before merge/deploy:

- `GET /api/v1/health` returns 200.
- Auth register/login works from frontend and direct API call.
- Expense CRUD and dashboard analytics endpoints respond correctly.
- Automation webhook path tested at least once end-to-end.
- If RAG/MCP code changed: manually confirm embeddings land in the `embeddings` table on expense writes, and that `/mcp` rejects calls without a valid bearer token.

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

5. `psycopg.OperationalError: ... Name or service not known` on Render

- See section 12 -- DB host DNS resolution failed, most likely a deleted free-tier database.

---

## 15) Git & Change Management

- Use focused commits with clear prefixes (`fix:`, `feat:`, `deploy:`, `docs:`).
- Keep infra changes (`render.yaml`, env contracts) explicit in commit messages.
- Push only after tests pass or risk is explicitly acknowledged.
- Do not add `Co-Authored-By` / session-link trailers to commit messages in this repo.

---

## 16) Definition of Done (Agentic)

A task is done when:

- Code changes are minimal and correct.
- Relevant tests pass.
- Runtime behavior validated (local or deployed as applicable).
- Docs/env instructions updated when behavior or deployment contracts change.
- No secrets introduced into tracked files.

---

## 17) Agent Tooling Snapshot

This section documents the AI agent configuration used to develop this
codebase (Claude Code CLI) -- separate from the application's own MCP/RAG/n8n
architecture documented in the sections above. It's a snapshot, not a live
contract: skill and MCP server availability depends on the operator's own
Claude Code setup and can differ session to session. Standard/built-in
Claude capabilities are out of scope here -- only what's connected or
configured in this specific setup is covered.

### 17.1 Summary

| Category | Count | Notes |
|---|---|---|
| MCP servers connected to the agent | 4 | 3 Google Workspace connectors (unauthenticated this session), 1 IDE bridge |
| Custom skills available | 16 | Design, review, config, scheduling, and reference skills; none triggered while building this project |
| Tools available | ~30, in 11 categories | File/code, execution, orchestration, planning, scheduling, delivery, search, feedback, IDE bridge, Workspace connectors |
| Sub-agent types available | 6 | `general-purpose`, `Explore`, `Plan`, `claude-code-guide`, `statusline-setup`, `fork` |
| Sub-agents actually spawned | 0 | All work done in the primary agent loop, no delegation |

### 17.2 MCP Servers

| Server | Primary Function | Tools Exposed | Used Building This Project |
|---|---|---|---|
| `claude_ai_Gmail` | Read/send email via the connected Gmail account | `authenticate`, `complete_authentication` (functional tools unlock post-auth) | No |
| `claude_ai_Google_Calendar` | Read/create/modify calendar events | `authenticate`, `complete_authentication` | No |
| `claude_ai_Google_Drive` | Search/read/write files in the connected Google Drive | `authenticate`, `complete_authentication` | No |
| `ide` | Bridges the session to the connected code editor | `executeCode` (run code in the editor's kernel), `getDiagnostics` (pull lint/type errors from open files) | No -- editor diagnostics surfaced automatically instead |

Not to be confused with `backend/app/mcp/server.py` -- an MCP server this
agent *built as application code* (see section 8), not one it is connected
to as a client.

### 17.3 Custom Skills

Skills are packaged instruction sets that load into the agent's context when
invoked, either by the agent recognizing a matching task or by explicit
command. None were invoked while building this project -- the actual work
(code analysis, implementation, git operations, documentation) didn't match
any skill's trigger conditions.

| Skill | Purpose |
|---|---|
| `design` | Draft multi-artboard visual designs (UI mockups, landing pages, posters) as a Claude Design canvas artifact |
| `dataviz` | Design-system guidance for building charts/graphs/dashboards consistently |
| `artifact-design` | Design calibration pass required before authoring any published Artifact |
| `artifact-diagramming` | Guidance for inline-SVG diagrams inside Artifacts |
| `artifact-capabilities` | Reference for runtime capabilities (live data, persistence, multi-viewer state) available to published Artifacts |
| `update-config` | Configure the Claude Code harness (`settings.json`) -- hooks, permissions, env vars |
| `keybindings-help` | Customize Claude Code keyboard shortcuts |
| `code-review` | Run a diff/PR review at a specified effort level, optionally auto-fixing findings |
| `simplify` | Review changed code for reuse/simplification/efficiency and apply fixes |
| `fewer-permission-prompts` | Scan transcripts and add a permission allowlist to reduce prompt friction |
| `loop` | Run a prompt or slash command on a recurring interval |
| `schedule` | Create/manage cron-scheduled cloud agent routines |
| `claude-api` | Reference for Claude API/Anthropic SDK usage (models, pricing, tool use, caching) |
| `claude-in-chrome` | Automate an existing Chrome session (click, fill forms, screenshot, read console) |
| `run` | Launch and drive this project's app to verify a change works live |
| `init` | Bootstrap a new `CLAUDE.md` with codebase documentation |
| `security-review` | Security review of pending changes on the current branch |

No skills live in a local `/mnt/skills/` path in this environment -- that
path is specific to Claude's hosted code-execution sandbox, not the Windows
Claude Code CLI. The list above is sourced from the CLI's built-in and
plugin-provided skill registry instead.

### 17.4 Available Tools

| Category | Tools | Used Building This Project |
|---|---|---|
| File & code | `Read`, `Write`, `Edit`, `Glob`, `Grep` | Yes -- all five |
| Execution | `Bash`, `PowerShell` | Yes -- both |
| Orchestration & agents | `Agent`, `ListAgents`, `SendMessage` | No |
| Planning & user interaction | `AskUserQuestion`, `EnterPlanMode`/`ExitPlanMode`, `EndConversation` | `AskUserQuestion` only |
| Scheduling & background work | `ScheduleWakeup`, `CronCreate`/`CronList`/`CronDelete`, `TaskOutput`/`TaskStop`, `RemoteTrigger` | No |
| Delivery & publishing | `Artifact`, `SendUserFile`, `DesignSync`, `PushNotification` | `SendUserFile` only |
| Search & reference | `ToolSearch`, `WebSearch`, `WebFetch` | `ToolSearch`, `WebSearch` |
| Feedback & review | `SendFeedback`, `ReportFindings` | No |
| IDE bridge (MCP-backed) | `mcp__ide__executeCode`, `mcp__ide__getDiagnostics` | No |
| Google Workspace (MCP-backed) | `mcp__claude_ai_Gmail__*`, `mcp__claude_ai_Google_Calendar__*`, `mcp__claude_ai_Google_Drive__*` | No |

### 17.5 Sub-Agents

Sub-agents are isolated task runners launched via the `Agent` tool; each has
a fixed tool allowlist and, except for `fork`, starts with no memory of the
parent conversation.

| Sub-Agent | Tool Access | Purpose |
|---|---|---|
| `general-purpose` (default) | All tools | Open-ended multi-step research or implementation tasks |
| `Explore` | Read-only search tools (no Edit/Write/Agent) | Broad, read-only fan-out search across the codebase |
| `Plan` | All tools except Agent/Artifact/Edit/Write | Produce a step-by-step implementation plan without touching files |
| `claude-code-guide` | `Glob`, `Grep`, `Read`, `WebFetch`, `WebSearch` | Answer questions about Claude Code, the Agent SDK, the Claude API, or Claude Tag |
| `statusline-setup` | `Read`, `Edit` | Configure the CLI status line |
| `fork` | Inherits the parent session's full tool access and context | Continue the current conversation's work in a background copy of the session itself |

None were spawned while building this project -- all implementation,
research, and git work was done directly by the primary agent.
