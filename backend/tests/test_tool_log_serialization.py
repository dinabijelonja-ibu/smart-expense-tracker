from datetime import date

from app.services.tool_log_service import _to_json_compatible


def test_to_json_compatible_converts_nested_date_values() -> None:
    data = {
        "top": date(2026, 3, 2),
        "nested": {
            "inner": date(2026, 3, 1),
        },
    }

    converted = _to_json_compatible(data)

    assert converted["top"] == "2026-03-02"
    assert converted["nested"]["inner"] == "2026-03-01"
