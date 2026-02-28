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

## 5.1 What to Embed

- Monthly spending summaries
- Category growth reports
- Budget goals
- Optional: financial knowledge documents

## 5.2 Embedding Pipeline

1. Generate monthly summary text:
   "In January you spent 450 BAM on food, 300 BAM on rent..."
2. Generate embedding via LLM embedding API.
3. Store in pgvector table.

Trigger embedding regeneration:

- End of month
- Major spending change

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
