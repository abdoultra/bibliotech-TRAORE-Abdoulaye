"""Borrowing outcomes and refusal priorities, independent of CLI routing."""

from pathlib import Path

import pytest

import bibliotech


@pytest.mark.parametrize(
    ("member_id", "book_id", "message"),
    [
        ("M004", "B002", "Refus : membre inactif"),
        ("M001", "B002", "Refus : emprunts en retard"),
        ("M005", "B001", "Refus : deja emprunte par ce membre"),
        ("M005", "B003", "Refus : plus d'exemplaire disponible"),
        ("M999", "B002", "Erreur : membre inconnu"),
        ("M005", "B999", "Erreur : livre inconnu"),
    ],
)
def test_refused_borrow_does_not_change_loans(
    library, capsys, member_id, book_id, message
):
    path = Path(bibliotech.DATA) / "loans.csv"
    saved = path.read_bytes()
    loans = [dict(loan) for loan in library.loans]
    assert library.borrow(member_id, book_id) is False
    assert capsys.readouterr().out == message + "\n"
    assert library.loans == loans
    assert path.read_bytes() == saved


def test_borrow_limit_is_enforced(library, capsys):
    assert library.borrow("M005", "B005") is True
    assert library.borrow("M005", "B002") is True
    capsys.readouterr()
    assert library.borrow("M005", "B007") is False
    assert capsys.readouterr().out == "Refus : limite d'emprunts atteinte (3)\n"


def test_successful_borrow_is_saved_with_expected_due_date(library, capsys):
    assert library.borrow("M005", "B005") is True
    assert library.loans[-1] == {
        "id": "L013",
        "member": "M005",
        "book": "B005",
        "start": "2026-10-21",
        "due": "2026-10-28",
        "returned": "",
        "fee": 0,
    }
    assert capsys.readouterr().out == (
        "Emprunt L013 enregistre : Inception pour Emma Laurent, "
        "retour avant le 2026-10-28\n"
    )
    assert bibliotech.Library().loans[-1] == library.loans[-1]


def test_unknown_member_is_checked_before_unknown_book(library, capsys):
    assert library.borrow("M999", "B999") is False
    assert capsys.readouterr().out == "Erreur : membre inconnu\n"


def test_inactive_member_is_checked_before_overdue_loan(library, capsys):
    member = library.find_member("M001")
    member["active"] = False
    assert library.borrow("M001", "B002") is False
    assert capsys.readouterr().out == "Refus : membre inactif\n"


def test_limit_is_checked_before_duplicate_book(library, capsys):
    assert library.borrow("M005", "B005") is True
    assert library.borrow("M005", "B002") is True
    capsys.readouterr()
    assert library.borrow("M005", "B005") is False
    assert capsys.readouterr().out == "Refus : limite d'emprunts atteinte (3)\n"
