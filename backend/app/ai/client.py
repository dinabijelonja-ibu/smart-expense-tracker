import json
from urllib import error, request

from app.core.config import settings


class LLMClientError(Exception):
    pass


def _extract_text_content(content: str | list | None) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return ""


def chat_completion(*, messages: list[dict], tools: list[dict]) -> dict:
    if not settings.llm_api_key:
        raise LLMClientError("LLM_API_KEY is not configured")

    payload = {
        "model": settings.llm_model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0,
    }

    req = request.Request(
        f"{settings.llm_base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.llm_api_key}",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise LLMClientError(f"LLM HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise LLMClientError(f"LLM request failed: {exc.reason}") from exc

    choices = body.get("choices", [])
    if not choices:
        raise LLMClientError("LLM returned no choices")

    message = choices[0].get("message", {})
    return {
        "role": "assistant",
        "content": _extract_text_content(message.get("content")),
        "tool_calls": message.get("tool_calls") or [],
    }
