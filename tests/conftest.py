"""Shared isolated library for business rule tests."""

import shutil
from datetime import date
from pathlib import Path

import pytest

import bibliotech

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def library(tmp_path, monkeypatch):
    """Library on temporary data, fixed at 21 October 2026."""
    data_dir = tmp_path / "data"
    shutil.copytree(DATA_DIR, data_dir)
    monkeypatch.setattr(bibliotech, "DATA", str(data_dir))
    monkeypatch.setattr(bibliotech, "TODAY", date(2026, 10, 21))
    return bibliotech.Library()
