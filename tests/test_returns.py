"""Exact CLI and CSV regression checks for zero-fee returns."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

import bibliotech

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("loan_id", "expected_output", "expected_row"),
    [
        (
            "L006",
            "Retour enregistre : Dune. Retard : 0 jour(s). Penalite : 0.00 EUR\n",
            "L006;M005;B001;2026-10-10;2026-10-31;2026-10-21;0.00",
        ),
        (
            "L005",
            "Retour enregistre : Clean Code. Retard : 10 jour(s). "
            "Penalite : 0.00 EUR\n",
            "L005;M003;B004;2026-09-20;2026-10-11;2026-10-21;0.00",
        ),
    ],
    ids=["on_time", "late_premium"],
)
def test_zero_fee_return_keeps_exact_output_and_csv(
    library, loan_id, expected_output, expected_row
):
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "bibliotech.py"),
            "return",
            loan_id,
            "--today",
            "2026-10-21",
        ],
        cwd=Path(bibliotech.DATA).parent,
        env={**os.environ, "BIBLIOTECH_DATA": bibliotech.DATA},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout == expected_output
    rows = (
        (Path(bibliotech.DATA) / "loans.csv").read_text(encoding="utf-8").splitlines()
    )
    assert [row for row in rows if row.startswith(loan_id + ";")] == [expected_row]
