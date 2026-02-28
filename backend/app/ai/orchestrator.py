import json
import uuid

from sqlalchemy.orm import Session

from app.ai.client import LLMClientError, chat_completion
from app.mcp.tools import TOOL_DEFINITIONS, execute_tool
from app.rag.service import RAGError, retrieve_context
from app.services.tool_log_service import log_tool_call

SYSTEM_PROMPT = (
    "You are a financial assistant for Smart Expense Tracker. "
    "For any financial data operation, use available tools. "
    "Never invent numbers. Keep responses concise and clear."
)


def _build_grounded_system_prompt(retrieved_chunks: list[str]) -> str:
    if not retrieved_chunks:
        return SYSTEM_PROMPT

    chunks = "\n".join([f"- {chunk}" for chunk in retrieved_chunks])
    return (
        f"{SYSTEM_PROMPT}\n"
        "Use the following retrieved financial context whenever it is relevant. "
        "Reference concrete values from it and do not fabricate missing facts.\n"
        f"Retrieved Context:\n{chunks}"
    )


def run_ai_chat(*, db: Session, user_id: uuid.UUID, user_message: str) -> str:
    if not user_message.strip():
        return "Please provide a message."

    try:
        retrieved_context = retrieve_context(db, user_id=user_id, question=user_message)
    except RAGError:
        retrieved_context = []

    messages: list[dict] = [
        {"role": "system", "content": _build_grounded_system_prompt(retrieved_context)},
        {"role": "user", "content": user_message.strip()},
    ]

    max_iterations = 4
    for _ in range(max_iterations):
        try:
            assistant_message = chat_completion(messages=messages, tools=TOOL_DEFINITIONS)
        except LLMClientError:
            return "AI is currently unavailable. Please check LLM configuration and try again."

        tool_calls = assistant_message.get("tool_calls", [])
        content = assistant_message.get("content", "")

        if not tool_calls:
            return content or "I could not produce a response."

        messages.append(
            {
                "role": "assistant",
                "content": content or "",
                "tool_calls": tool_calls,
            }
        )

        for tool_call in tool_calls:
            function_block = tool_call.get("function", {})
            tool_name = function_block.get("name", "")
            arguments_json = function_block.get("arguments", "{}")

            try:
                tool_result = execute_tool(
                    db,
                    user_id=user_id,
                    tool_name=tool_name,
                    arguments_json=arguments_json,
                )
            except Exception as exc:
                tool_result = {"error": str(exc)}

            try:
                parsed_arguments = json.loads(arguments_json) if arguments_json else {}
            except json.JSONDecodeError:
                parsed_arguments = {"raw": arguments_json}

            log_tool_call(
                db,
                user_id=user_id,
                tool_name=tool_name,
                arguments=parsed_arguments,
                result=tool_result,
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "name": tool_name,
                    "content": json.dumps(tool_result),
                }
            )

    return "I reached the tool-calling limit for this request. Please try again with a narrower question."
