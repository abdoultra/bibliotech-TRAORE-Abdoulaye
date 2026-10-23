"""ISO date conversion contract, independent of the system clock."""

from datetime import date

import pytest

from bibliotech import parse_date


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2026-10-21", date(2026, 10, 21)),
        ("2024-02-29", date(2024, 2, 29)),
        ("2026-01-01", date(2026, 1, 1)),
    ],
)
def test_parse_date(text, expected):
    assert parse_date(text) == expected


@pytest.mark.parametrize("text", ["2026-13-01", "2026-02-29", "21/10/2026", ""])
def test_parse_date_rejects_invalid_dates(text):
    with pytest.raises(ValueError):
        parse_date(text)
