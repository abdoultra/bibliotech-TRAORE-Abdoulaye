"""Shared isolated library for business rule tests."""

import shutil
from datetime import date
from pathlib import Path

import pytest

import bibliotech

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def library(tmp_path, monkeypatch):
    """Copy the reference CSVs and fix the date at 21 October 2026.

    Borrow tests depend on the supplied data/ snapshot: M004 is inactive;
    M001 has overdue loan L004; M005 currently borrows B001 (L006), has
    no overdue loan and has a standard limit of three loans; B003 has no
    available copies. B005 and B002 can be borrowed by M005, after which
    B007 is refused by the limit. IDs end at L012, so the next is L013.
    B005 is a DVD, due on 2026-10-28 when borrowed on the fixed date.

    Return tests use L006 (Dune, due 2026-10-31) for an early return and
    L005 (Clean Code, premium member M003, due 2026-10-11) for a late
    premium return. Update these scenarios deliberately if CSVs change.
    Each test receives a fresh temporary copy; source CSVs stay unchanged.
    """
    data_dir = tmp_path / "data"
    shutil.copytree(DATA_DIR, data_dir)
    monkeypatch.setattr(bibliotech, "DATA", str(data_dir))
    monkeypatch.setattr(bibliotech, "TODAY", date(2026, 10, 21))
    return bibliotech.Library()
