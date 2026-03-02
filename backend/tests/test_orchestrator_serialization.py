from datetime import date
import json

from app.ai.orchestrator import _safe_json_dumps


def test_safe_json_dumps_serializes_date() -> None:
    payload = {"date": date(2026, 3, 2), "amount": 11.0}

    serialized = _safe_json_dumps(payload)
    parsed = json.loads(serialized)

    assert parsed["date"] == "2026-03-02"
    assert parsed["amount"] == 11.0
