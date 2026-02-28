# n8n Workflows

This folder contains starter n8n workflow JSON templates:

- `weekly_report_workflow.json`
- `budget_alert_workflow.json`
- `receipt_ingest_workflow.json` (optional)

## Required n8n Environment Variables

- `API_BASE_URL` (for local backend: `http://localhost:8000`)
- `USER_ID` (target user UUID)
- `AUTOMATION_API_KEY` (must match backend `AUTOMATION_API_KEY`)

## Backend Endpoints Used

- `GET /api/v1/automation/weekly-report?user_id=<uuid>`
- `GET /api/v1/automation/budget-alerts?user_id=<uuid>&threshold=80`
- `POST /api/v1/automation/receipt-ingest`
