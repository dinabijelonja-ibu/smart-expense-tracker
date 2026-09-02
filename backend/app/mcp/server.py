"""A real Model Context Protocol server.

`app/mcp/tools.py` is the *internal* tool-calling layer: OpenAI-style function
schemas fed to the LLM inside `app.ai.orchestrator`'s in-process chat loop.
It has never spoken the actual Model Context Protocol (JSON-RPC over a
stdio/HTTP transport, `tools/list` + `tools/call`), despite the module's name.

This module is the real thing: it exposes the same three tools over MCP's
streamable-HTTP transport (mounted at `/mcp` by `app.main`), so any
MCP-compatible client -- Claude Desktop, Claude Code, or any other MCP
client -- can connect directly to this backend and call them, independent of
the in-app AI chat.

Both layers share one source of truth for the actual business logic:
`app.mcp.tools.execute_tool`. This module only adapts that dispatcher to the
MCP protocol -- schema generation from type hints, transport, and per-call
user authentication -- the same way `app/mcp/tools.py` adapts it to
OpenAI-style function calling.

Authentication: MCP tool calls happen outside FastAPI's normal
`Depends(get_current_user)` request flow, so each call must carry its own
`Authorization: Bearer <token>` header using the same JWT issued by
`POST /api/v1/auth/login` or `/auth/register`. `resolve_user_id` verifies
that token with the app's existing `decode_access_token` -- request headers
are client-supplied input and are never trusted as an identity assertion on
their own.
"""

import json
import uuid

from jose import JWTError
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.mcp.tools import execute_tool
from app.services.tool_log_service import log_tool_call

mcp_server = MCPServer(
    name="smart-expense-tracker",
    instructions=(
        "Tools for the Smart Expense Tracker. Every call requires an "
        "'Authorization: Bearer <token>' header carrying a JWT issued by "
        "POST /api/v1/auth/login or /api/v1/auth/register. Each call reads "
        "and writes only that token's own user data."
    ),
)


class McpAuthError(Exception):
    """Raised when a tool call has no valid Smart Expense Tracker JWT."""


def resolve_user_id(headers: dict | None) -> uuid.UUID:
    """Resolve the authenticated user id from request headers.

    Kept free of any `Context`/transport dependency so it is unit-testable
    with plain dicts.
    """
    headers = headers or {}
    raw = headers.get("authorization") or headers.get("Authorization")
    if not raw or not raw.lower().startswith("bearer "):
        raise McpAuthError("Missing 'Authorization: Bearer <token>' header")

    token = raw.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
        return uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError, TypeError) as exc:
        raise McpAuthError("Invalid or expired token") from exc


def _run_tool(ctx: Context, tool_name: str, arguments: dict) -> dict:
    try:
        user_id = resolve_user_id(dict(ctx.headers) if ctx.headers else None)
    except McpAuthError as exc:
        raise ToolError(str(exc)) from exc

    clean_arguments = {key: value for key, value in arguments.items() if value is not None}
    arguments_json = json.dumps(clean_arguments, default=str)

    db = SessionLocal()
    try:
        result = execute_tool(db, user_id=user_id, tool_name=tool_name, arguments_json=arguments_json)
    except (ValueError, KeyError) as exc:
        raise ToolError(str(exc)) from exc
    else:
        log_tool_call(db, user_id=user_id, tool_name=f"mcp:{tool_name}", arguments=clean_arguments, result=result)
        return result
    finally:
        db.close()


@mcp_server.tool(name="add_expense", description="Add a new expense for the authenticated user")
def add_expense(ctx: Context, amount: float, category: str, date: str, description: str | None = None) -> dict:
    return _run_tool(
        ctx,
        "add_expense",
        {"amount": amount, "category": category, "date": date, "description": description},
    )


@mcp_server.tool(name="get_category_summary", description="Get spending summary by category for a given month")
def get_category_summary(ctx: Context, month: str, category: str | None = None) -> dict:
    return _run_tool(ctx, "get_category_summary", {"month": month, "category": category})


@mcp_server.tool(
    name="forecast_end_of_month", description="Calculate deterministic end-of-month spending projection"
)
def forecast_end_of_month(ctx: Context) -> dict:
    return _run_tool(ctx, "forecast_end_of_month", {})


mcp_app = mcp_server.streamable_http_app(streamable_http_path="/")
