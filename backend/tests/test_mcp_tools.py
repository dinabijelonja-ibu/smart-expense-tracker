from datetime import date

import pytest

from app.mcp.tools import _parse_month


def test_parse_month_valid() -> None:
    parsed = _parse_month("2026-03")

    assert parsed == date(2026, 3, 1)


@pytest.mark.parametrize("value", ["2026/03", "2026-00", "march-2026", "2026-13"])
def test_parse_month_invalid(value: str) -> None:
    with pytest.raises(Exception):
        _parse_month(value)
