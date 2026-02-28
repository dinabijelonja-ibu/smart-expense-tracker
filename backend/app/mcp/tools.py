import json
import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.services.analytics_service import category_summary, forecast_end_of_month
from app.services.expense_service import create_expense, get_expense_category_map, serialize_expense


TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "add_expense",
            "description": "Add a new expense for the authenticated user",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number"},
                    "category": {"type": "string"},
                    "description": {"type": "string"},
                    "date": {"type": "string"},
                },
                "required": ["amount", "category", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_category_summary",
            "description": "Get spending summary by category for a given month",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "month": {"type": "string"},
                },
                "required": ["month"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forecast_end_of_month",
            "description": "Calculate deterministic end-of-month spending projection",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]


def _parse_month(month_value: str) -> date:
    parts = month_value.split("-")
    if len(parts) != 2:
        raise ValueError("month must be in YYYY-MM format")
    year = int(parts[0])
    month = int(parts[1])
    return date(year, month, 1)


def execute_tool(db: Session, *, user_id: uuid.UUID, tool_name: str, arguments_json: str) -> dict:
    try:
        arguments = json.loads(arguments_json) if arguments_json else {}
    except json.JSONDecodeError as exc:
        raise ValueError("Tool arguments must be valid JSON") from exc

    if tool_name == "add_expense":
        expense_date = date.fromisoformat(arguments["date"])
        expense = create_expense(
            db,
            user_id=user_id,
            amount=float(arguments["amount"]),
            category_name=arguments["category"],
            description=arguments.get("description"),
            expense_date=expense_date,
        )
        category_map = get_expense_category_map(db, [expense])
        return serialize_expense(expense, category_map.get(expense.category_id, "unknown"))

    if tool_name == "get_category_summary":
        month_raw = arguments.get("month")
        if not month_raw:
            raise ValueError("month is required")
        summary = category_summary(db, user_id=user_id, target=_parse_month(month_raw))
        requested_category = arguments.get("category")
        if requested_category:
            filtered = [item for item in summary["items"] if item["category"] == requested_category.strip().lower()]
            return {"month": summary["month"], "items": filtered}
        return summary

    if tool_name == "forecast_end_of_month":
        return forecast_end_of_month(db, user_id=user_id)

    raise ValueError(f"Unknown tool: {tool_name}")
