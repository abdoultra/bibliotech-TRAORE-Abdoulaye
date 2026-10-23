"""The report data can be inspected without printing reminders."""

from datetime import date

import pytest

import bibliotech


def test_overdue_data_has_expected_order_days_and_fees(library, capsys):
    results = library.find_overdue_loans()
    assert [item.loan_id for item in results] == ["L003", "L004", "L005", "L007"]
    assert [item.days_late for item in results] == [15, 13, 10, 3]
    assert [item.fee for item in results] == pytest.approx([7.5, 6.5, 0, 0.3])
    assert results[0].book["id"] == "B003"
    assert results[0].member["id"] == "M002"
    assert capsys.readouterr().out == ""


def test_no_overdue_before_due_dates(library, monkeypatch, capsys):
    monkeypatch.setattr(bibliotech, "TODAY", date(2026, 8, 1))
    assert library.find_overdue_loans() == []
    assert capsys.readouterr().out == ""


def test_due_today_is_not_overdue_and_returned_is_ignored(library):
    loan = library.loans[0]
    library.loans = [
        dict(loan, id="L101", returned="", due="2026-10-21"),
        dict(loan, id="L102", returned="2026-10-20", due="2026-10-01"),
    ]
    assert library.find_overdue_loans() == []


def test_overdue_orphan_is_reported_once(library, caplog):
    library.loans = [
        dict(library.loans[0], returned="", due="2026-10-01", book="MISSING")
    ]
    assert library.find_overdue_loans() == []
    assert len(caplog.records) == 1
    assert "introuvable" in caplog.text
