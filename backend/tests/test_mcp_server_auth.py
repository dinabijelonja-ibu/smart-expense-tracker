import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token
from app.mcp.server import McpAuthError, mcp_server, resolve_user_id


def test_resolve_user_id_valid_bearer_token() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(str(user_id))

    resolved = resolve_user_id({"authorization": f"Bearer {token}"})

    assert resolved == user_id


def test_resolve_user_id_is_case_insensitive_to_header_name() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(str(user_id))

    resolved = resolve_user_id({"Authorization": f"Bearer {token}"})

    assert resolved == user_id


def test_resolve_user_id_missing_headers_raises() -> None:
    with pytest.raises(McpAuthError):
        resolve_user_id(None)

    with pytest.raises(McpAuthError):
        resolve_user_id({})


def test_resolve_user_id_wrong_scheme_raises() -> None:
    with pytest.raises(McpAuthError):
        resolve_user_id({"authorization": "Token abc123"})


def test_resolve_user_id_garbage_token_raises() -> None:
    with pytest.raises(McpAuthError):
        resolve_user_id({"authorization": "Bearer not-a-real-jwt"})


def test_resolve_user_id_expired_token_raises() -> None:
    expired = jwt.encode(
        {"sub": str(uuid.uuid4()), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(McpAuthError):
        resolve_user_id({"authorization": f"Bearer {expired}"})


def test_resolve_user_id_non_uuid_subject_raises() -> None:
    token = create_access_token("not-a-uuid")

    with pytest.raises(McpAuthError):
        resolve_user_id({"authorization": f"Bearer {token}"})


def test_mcp_server_registers_the_expected_tools() -> None:
    tools = asyncio.run(mcp_server.list_tools())
    names = {tool.name for tool in tools}

    assert names == {"add_expense", "get_category_summary", "forecast_end_of_month"}
