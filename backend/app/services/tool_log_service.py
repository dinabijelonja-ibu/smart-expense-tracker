import uuid
import json

from sqlalchemy.orm import Session

from app.models.tool_call_log import ToolCallLog


def _to_json_compatible(value: dict) -> dict:
    return json.loads(json.dumps(value, default=str))


def log_tool_call(
    db: Session,
    *,
    user_id: uuid.UUID,
    tool_name: str,
    arguments: dict,
    result: dict,
) -> None:
    row = ToolCallLog(
        user_id=user_id,
        tool_name=tool_name,
        arguments=_to_json_compatible(arguments),
        result=_to_json_compatible(result),
    )
    db.add(row)
    db.commit()
