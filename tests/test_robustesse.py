"""Regression checks for malformed data and plugin failures."""

import importlib.util
import logging
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def app(tmp_path):
    spec = importlib.util.spec_from_file_location("bibliotech", ROOT / "bibliotech.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = tmp_path / "data"
    shutil.copytree(ROOT / "data", data)
    module.DATA = str(data)
    module.TODAY = date(2026, 10, 21)
    return module


def test_list_without_today(app):
    result = subprocess.run(
        [sys.executable, str(ROOT / "bibliotech.py"), "list"],
        env={**os.environ, "BIBLIOTECH_DATA": app.DATA},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0
    assert "Dune" in result.stdout
    assert result.stderr == ""
    app.TODAY = None
    assert app.get_today() == date.today()


@pytest.mark.parametrize("missing", ["book", "member"])
def test_orphan_loan_is_skipped(app, tmp_path, caplog, missing):
    library = app.Library()
    orphan = dict(library.loans[0], id="L999", returned="", due="2020-01-01")
    orphan[missing] = "MISSING"
    library.loans = [orphan]
    with caplog.at_level(logging.WARNING):
        library.report()
        library.overdue()
        output = tmp_path / "export.csv"
        library.export(str(output), ";")
        library.return_loan("L999")
    assert "L999" in caplog.text
    assert len(output.read_text(encoding="utf-8").splitlines()) == 1
    assert orphan["returned"] == ""
    assert library.available_copies("MISSING") == 0


def test_overdue_ignores_returned_orphans(app, caplog, monkeypatch):
    library = app.Library()
    library.loans = [dict(library.loans[0], book="MISSING", returned="2020-01-01")]
    calls = []
    original = library.loan_parties

    def track(loan):
        calls.append(loan["id"])
        return original(loan)

    monkeypatch.setattr(library, "loan_parties", track)
    library.overdue()
    assert calls == []
    assert caplog.records == []
    library.loans = [dict(library.loans[0], returned="", due="2020-01-01")]
    library.overdue()
    assert calls == [library.loans[0]["id"]]
    assert len(caplog.records) == 1


@pytest.mark.parametrize("invalid", ["", "BAD", "Labc", "X999", "L-2", "L1.5"])
def test_invalid_loan_id_does_not_break_borrow(app, caplog, invalid):
    library = app.Library()
    library.loans = [dict(library.loans[0], id=invalid, returned="2020-01-01")]
    assert library.borrow("M005", "B005") is True
    assert library.loans[-1]["id"] == "L001"
    assert "Identifiant" in caplog.text


def test_plugin_failure_is_logged_and_other_plugins_continue(app, caplog):
    library = app.Library()

    def broken(event, payload):
        raise RuntimeError("plugin failure")

    library.register_plugin("broken", broken)
    library.register_plugin("healthy", lambda event, payload: "ok", priority=1)
    assert library.run_plugins("check") == ["ok"]
    assert "broken" in caplog.text
    assert "plugin failure" in caplog.text
    assert caplog.records[0].exc_info is not None


def test_plugin_default_options_are_independent(app):
    library = app.Library()
    library.register_plugin("first", lambda *args, **kwargs: None)
    library.register_plugin("second", lambda *args, **kwargs: None)
    library.plugins["first"]["options"]["changed"] = True
    assert library.plugins["second"]["options"] == {}


def test_price_cannot_execute_python(app, tmp_path):
    marker = tmp_path / "executed.txt"
    path = Path(app.DATA) / "books.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    fields = lines[1].split(";")
    fields[4] = f"__import__('pathlib').Path({str(marker)!r}).touch()"
    lines[1] = ";".join(fields)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        app.Library()
    assert not marker.exists()


def test_export_preserves_utf8(app, tmp_path):
    path = Path(app.DATA) / "books.csv"
    path.write_text(
        path.read_text(encoding="utf-8").replace("Dune", "Été à Paris"),
        encoding="utf-8",
    )
    output = tmp_path / "export.csv"
    app.Library().export(str(output), ";")
    assert "Été à Paris" in output.read_text(encoding="utf-8")
