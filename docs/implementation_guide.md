# Smart Expense Tracker – AI-Driven Implementation Guide (Detailed Version)

## Project Goal

Build a production-structured Smart Expense Tracker demonstrating:

- MCP (Model Context Protocol) → Structured tool calling
- RAG (Retrieval-Augmented Generation) → Grounded financial reasoning
- n8n → Event-driven AI automation

Mandatory Stack:

- Frontend: React
- Backend: Python (FastAPI)
- Database: PostgreSQL + pgvector

The system must strictly separate deterministic financial logic from AI reasoning.

============================================================

# 1. SYSTEM ARCHITECTURE

React Frontend
↓
FastAPI Backend
├── REST Routers
├── Services (deterministic logic)
├── MCP Tool Layer
├── RAG Module
↓
PostgreSQL (relational data + pgvector)
↓
LLM API
↓
n8n Automation Layer

Key Principle:
LLM never directly queries the database.
All financial computations occur in deterministic Python services.

============================================================

# 2. DATABASE IMPLEMENTATION

## 2.1 Initial Setup

1. Install PostgreSQL
2. Create database:
   CREATE DATABASE smart_expense_tracker;
3. Connect and enable pgvector:
   CREATE EXTENSION IF NOT EXISTS vector;

## 2.2 SQLAlchemy Models (Required)

users

- id (UUID, PK)
- email (unique)
- password_hash
- created_at

categories

- id
- user_id (FK)
- name

expenses

- id
- user_id (FK)
- category_id (FK)
- amount (numeric)
- description
- date
- created_at

budgets

- id
- user_id (FK)
- category_id (FK)
- monthly_limit

embeddings

- id
- user_id
- content (text)
- embedding (vector(1536) or model-specific size)
- metadata (JSON)

Use Alembic for migrations.

============================================================

# 3. BACKEND API SPECIFICATION (FastAPI)

## 3.1 Auth Endpoints

POST /auth/register
POST /auth/login

Return JWT.

## 3.2 Expense Endpoints

POST /expenses
GET /expenses
PUT /expenses/{id}
DELETE /expenses/{id}

Query parameters:

- start_date
- end_date
- category

## 3.3 Budget Endpoints

POST /budgets
GET /budgets

## 3.4 Analytics Endpoints

GET /analytics/monthly-summary
GET /analytics/category-summary
GET /analytics/forecast

All analytics must be computed in Python services.

============================================================

# 4. MCP IMPLEMENTATION (Tool Calling Layer)

> **Naming note (as implemented):** this section originally used "MCP" as a
> stand-in for "structured tool calling" generically. As implemented, the
> project has two distinct layers, because they solve different problems:
>
> - **`app/mcp/tools.py`** -- OpenAI-style function-calling schemas fed to
>   the LLM inside the in-process AI chat loop (`app/ai/orchestrator.py`).
>   This is *not* the Model Context Protocol; it never was a standalone
>   protocol server.
> - **`app/mcp/server.py`** -- the actual [Model Context Protocol](https://modelcontextprotocol.io):
>   a real MCP server (`mcp` Python SDK, streamable-HTTP transport) mounted
>   at `/mcp` on the FastAPI app, so any MCP-compatible client (Claude
>   Desktop, Claude Code, etc.) can call these tools directly and
>   independently of the in-app chat, authenticated via the same JWT as the
>   REST API.
>
> Both layers call the same underlying dispatcher (`execute_tool` below), so
> there is one source of truth for the actual business logic -- only the
> protocol adapter differs.

## 4.1 MCP Architecture

Create a dedicated module:
app/mcp/tools.py

Each tool wraps a deterministic service function.

## 4.2 Tool Schemas (Example JSON Definitions)

Tool: add_expense
{
"name": "add_expense",
"description": "Add a new expense for the authenticated user",
"parameters": {
"type": "object",
"properties": {
"amount": {"type": "number"},
"category": {"type": "string"},
"description": {"type": "string"},
"date": {"type": "string"}
},
"required": ["amount", "category", "date"]
}
}

Tool: get_category_summary
{
"name": "get_category_summary",
"parameters": {
"type": "object",
"properties": {
"category": {"type": "string"},
"month": {"type": "string"}
},
"required": ["category", "month"]
}
}

Tool: forecast_end_of_month
{
"name": "forecast_end_of_month",
"parameters": {
"type": "object",
"properties": {}
}
}

## 4.3 MCP Execution Flow

1. Frontend sends chat message to backend.
2. Backend sends message + tool definitions to LLM.
3. If LLM selects a tool:
   - Execute deterministic service.
   - Return JSON result to LLM.

4. LLM produces final natural language response.

Log every tool call in database for auditing.

============================================================

# 5. RAG IMPLEMENTATION

## 5.1 What to Embed (as implemented)

Three granularities, all stored in the same `embeddings` table and
distinguished by a `metadata.type` / `metadata.key` tag, so a similarity
search naturally picks whichever granularity best matches the question:

- **Per-expense** (`expense:<id>`) -- one line per expense ("On 2026-09-02
  you spent 12.50 on food: coffee (expense #341)."), for specific-transaction
  questions ("that coffee last Tuesday").
- **Daily summary** (`daily-summary:YYYY-MM-DD`) -- one row per day that has
  expenses, for "what happened yesterday / on the 12th" questions.
- **Monthly summary** (`monthly-summary:YYYY-MM`) -- one row per month, for
  "how did this month go" questions.

Budget goals and free-form financial knowledge documents are not embedded
today; they'd slot into this same table with their own `metadata.type`.

## 5.2 Embedding Pipeline (as implemented)

Regeneration is **write-time, not scheduled**: `app/services/expense_service.py`
calls `app.rag.service.sync_expense_related_embeddings` (or
`sync_expense_deletion`) after every expense create/update/delete, which
upserts that expense's own embedding plus the affected day's and month's
summary embeddings in the same request. This was chosen over "regenerate at
end of month" / "on major spending change" because those triggers require a
scheduler and are inherently stale between runs, whereas write-time sync
keeps every granularity always current with zero extra moving parts.

It is best-effort: `RAGError` (e.g. `LLM_API_KEY` unset, embeddings API
down) is caught and swallowed at the sync boundary, so a slow or unavailable
embeddings provider never blocks adding/editing/deleting an expense.

Two maintenance endpoints exist for cases write-time sync can't cover:

- `POST /api/v1/ai/embeddings/backfill` (JWT-authenticated) -- rebuilds all
  three granularities from a user's full expense history. Run once when
  enabling RAG on an account with pre-existing expenses.
- `POST /api/v1/automation/embeddings/daily-rebuild` (automation-key gated)
  -- re-syncs one day's embedding on demand. Intended as an n8n-scheduled
  nightly safety net (`docs/n8n/daily_embedding_rebuild_workflow.json`) that
  self-heals a day whose write-time sync failed, rather than as the primary
  sync mechanism.

## 5.3 Retrieval Flow

On user advisory question:

1. Generate embedding of question.
2. Perform vector similarity search (top 5).
3. Inject retrieved content into prompt:

Prompt Template Example:

System:
You are a financial assistant. Use ONLY the retrieved financial data.

Retrieved Context:
{retrieved_chunks}

User Question:
{question}

Answer clearly and reference numbers from the data.

============================================================

# 6. N8N AUTOMATION WORKFLOWS

## 6.1 Weekly AI Report

Trigger: Cron (Sunday 20:00)
Nodes:

- HTTP Request → GET /analytics/monthly-summary
- OpenAI Node → Generate report
- Email Node → Send report

LLM Prompt:
"Generate a concise weekly financial report based on this JSON data. Highlight overspending and give 2 improvement suggestions."

---

## 6.2 Budget Threshold Alert

Trigger: Webhook from backend OR scheduled check
Nodes:

- HTTP Request → GET budget usage
- IF Node → usage > 80%
- OpenAI Node → Generate warning
- Email/Push Node

---

## 6.3 Receipt OCR Workflow (Advanced)

Trigger: File upload webhook
Nodes:

- OCR Node
- OpenAI Node (parse structured JSON)
- HTTP Request → POST /expenses
- Confirmation message

============================================================

# 7. REACT FRONTEND SPECIFICATION

## Pages

- Login / Register
- Dashboard (charts + insights)
- Expenses List
- Budgets
- AI Chat

## AI Chat Behavior

Chat endpoint: POST /ai/chat

Backend handles:

- Tool calling
- RAG retrieval
- Final response

Frontend only renders conversation.

============================================================

# 8. FORECASTING LOGIC (Deterministic)

Implement Python service:

forecast_end_of_month():

- Calculate daily average spending
- Multiply by remaining days
- Add to current total
- Return projected total

LLM explains the result but does not compute it.

============================================================

# 9. DEVELOPMENT PHASES (DETAILED)

Phase 1 – Infrastructure

- Setup PostgreSQL + pgvector
- Setup FastAPI project
- Setup SQLAlchemy + Alembic
- Setup React app

Phase 2 – Core Features

- CRUD expenses
- Budget tracking
- Monthly analytics

Phase 3 – MCP

- Define tool schemas
- Implement tool execution handler
- Connect LLM tool-calling

Phase 4 – RAG

- Implement embedding generator
- Implement similarity search
- Integrate retrieval into advisory chat

Phase 5 – n8n

- Deploy n8n locally or via Docker
- Implement weekly report
- Implement budget alert
- Optional receipt OCR

============================================================

# 10. EVALUATION CRITERIA

The final system must demonstrate:

- Structured tool calling (MCP)
- Grounded advisory responses (RAG)
- Event-driven AI workflows (n8n)
- Deterministic financial logic separation
- Minimal hallucination risk
- Clean architecture

============================================================

# FINAL OBJECTIVE

Deliver a layered AI-powered financial assistant system.

Not a CRUD app with a chatbot.
A structured, auditable, automated AI-driven application demonstrating real engineering principles.
