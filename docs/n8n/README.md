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

## 3-Request Smoke Test (PowerShell)

Run this from the project root after backend is running on `http://127.0.0.1:8000`.

```powershell
$ErrorActionPreference = 'Stop'

function Get-JwtSub([string]$token) {
	$parts = $token.Split('.')
	if ($parts.Length -lt 2) { throw 'Invalid JWT' }
	$payload = $parts[1].Replace('-', '+').Replace('_', '/')
	switch ($payload.Length % 4) {
		2 { $payload += '==' }
		3 { $payload += '=' }
	}
	$json = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($payload))
	return ((ConvertFrom-Json $json).sub)
}

$email = "n8n.smoke.$(Get-Random)@example.com"
$authBody = @{ email = $email; password = 'password123' } | ConvertTo-Json -Compress
$register = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/v1/auth/register' -ContentType 'application/json' -Body $authBody
$token = $register.access_token
$userId = Get-JwtSub $token
$bearer = @{ Authorization = "Bearer $token" }
$today = (Get-Date).ToString('yyyy-MM-dd')

# Seed data
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/v1/expenses' -Headers $bearer -ContentType 'application/json' -Body (@{ amount = 15.5; category = 'food'; description = 'sandwich'; date = $today } | ConvertTo-Json -Compress) | Out-Null
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/v1/budgets' -Headers $bearer -ContentType 'application/json' -Body (@{ category = 'food'; monthly_limit = 50 } | ConvertTo-Json -Compress) | Out-Null

$automationHeaders = @{ 'X-Automation-Key' = 'change-this-automation-key' }

# 1) weekly-report
$weekly = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/v1/automation/weekly-report?user_id=$userId" -Headers $automationHeaders

# 2) budget-alerts
$alerts = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/v1/automation/budget-alerts?user_id=$userId&threshold=20" -Headers $automationHeaders

# 3) receipt-ingest
$receiptBody = @{ user_id = $userId; amount = 8.75; category = 'food'; description = 'coffee'; date = $today } | ConvertTo-Json -Compress
$receipt = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/v1/automation/receipt-ingest' -Headers $automationHeaders -ContentType 'application/json' -Body $receiptBody

"USER_ID=$userId"
"WEEKLY_REPORT=" + ($weekly | ConvertTo-Json -Compress)
"BUDGET_ALERTS=" + ($alerts | ConvertTo-Json -Compress)
"RECEIPT_INGEST=" + ($receipt | ConvertTo-Json -Compress)
```
