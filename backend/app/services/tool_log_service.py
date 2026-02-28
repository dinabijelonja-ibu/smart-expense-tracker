import uuid

from sqlalchemy.orm import Session

from app.models.tool_call_log import ToolCallLog


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
        arguments=arguments,
        result=result,
    )
    db.add(row)
    db.commit()
