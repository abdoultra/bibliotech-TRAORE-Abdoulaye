# BiblioTech v1.3
# gestion de la bibliotheque municipale
# auteur : stagiaire 2019, modifie par plusieurs personnes depuis

import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta

DATA = os.environ.get("BIBLIOTECH_DATA", "data")
TODAY = None
debug = False
LOGGER = logging.getLogger(__name__)
DAILY_FEES = {"book": 0.5, "dvd": 1.0, "magazine": 0.2}
DEFAULT_DAILY_FEE = 0.5
DISCOUNTS = {"student": 0.5, "premium": 1.0}
LOAN_DAYS = {"book": 21, "dvd": 7, "magazine": 3}
LOAN_LIMITS = {"student": 5, "premium": 8}
DEFAULT_LOAN_DAYS = 21
DEFAULT_MAX_LOANS = 3


def late_fee(days_late: int, kind: str, member_type: str, price: float) -> float:
    """Return the discounted late fee, capped at the document price."""
    if days_late <= 0:
        return 0.0
    fee = days_late * DAILY_FEES.get(kind, DEFAULT_DAILY_FEE)
    fee *= 1 - DISCOUNTS.get(member_type, 0.0)
    return round(min(fee, price), 2)


def parse_date(text: str) -> date:
    """Read the date format used by CSV files and the CLI."""
    return datetime.strptime(text, "%Y-%m-%d").date()


def find_by_id(items, item_id):
    """Return the first matching record, or None."""
    return next((item for item in items if item["id"] == item_id), None)


@dataclass(frozen=True)
class OverdueLoan:
    loan_id: str
    member: dict
    book: dict
    days_late: int
    fee: float


class Library:
    def __init__(self):
        self.books = []
        self.members = []
        self.loans = []
        self.plugins = {}
        self.load()

    def load(self):
        self.load_books()
        self.load_members()
        self.load_loans()
        if debug:
            print("chargement ok", len(self.books), len(self.members), len(self.loans))

    def load_books(self):
        with open(DATA + "/books.csv", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines[1:]:
            if line.strip() == "":
                continue
            x = line.strip().split(";")
            self.books.append(
                {
                    "id": x[0],
                    "title": x[1],
                    "author": x[2],
                    "kind": x[3],
                    "price": float(x[4]),
                    "copies": int(x[5]),
                }
            )

    def load_members(self):
        with open(DATA + "/members.csv", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines[1:]:
            if line.strip() == "":
                continue
            x = line.strip().split(";")
            a = x[4] == "1"
            self.members.append(
                {"id": x[0], "name": x[1], "email": x[2], "type": x[3], "active": a}
            )

    def load_loans(self):
        with open(DATA + "/loans.csv", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines[1:]:
            if line.strip() == "":
                continue
            x = line.strip().split(";")
            try:
                fee = float(x[6])
            except (ValueError, IndexError):
                fee = 0
            self.loans.append(
                {
                    "id": x[0],
                    "member": x[1],
                    "book": x[2],
                    "start": x[3],
                    "due": x[4],
                    "returned": x[5],
                    "fee": fee,
                }
            )

    def save(self):
        with open(DATA + "/loans.csv", "w", encoding="utf-8") as f:
            f.write("id;member_id;book_id;start;due;returned;fee\n")
            for x in self.loans:
                f.write(
                    x["id"]
                    + ";"
                    + x["member"]
                    + ";"
                    + x["book"]
                    + ";"
                    + x["start"]
                    + ";"
                    + x["due"]
                    + ";"
                    + x["returned"]
                    + ";"
                    + "%.2f" % x["fee"]
                    + "\n"
                )

    def find_book(self, book_id):
        return find_by_id(self.books, book_id)

    def find_member(self, member_id):
        return find_by_id(self.members, member_id)

    def find_loan(self, loan_id):
        return find_by_id(self.loans, loan_id)

    def loan_parties(self, loan):
        """Ignore orphan loans with a diagnostic instead of crashing."""
        book = self.find_book(loan["book"])
        member = self.find_member(loan["member"])
        if book is None or member is None:
            LOGGER.warning(
                "Emprunt %s ignore : livre ou membre introuvable", loan["id"]
            )
            return None
        return book, member

    def next_loan_id(self):
        numbers = []
        for loan in self.loans:
            match = re.fullmatch(r"L([0-9]+)", loan["id"])
            if match is None:
                LOGGER.warning("Identifiant d'emprunt invalide ignore : %s", loan["id"])
                continue
            numbers.append(int(match[1]))
        return f"L{max(numbers, default=0) + 1:03d}"

    def active_loan_count(self, mid):
        n = 0
        for x in self.loans:
            if x["member"] == mid and x["returned"] == "":
                n = n + 1
        return n

    def available_copies(self, bid):
        bk = self.find_book(bid)
        if bk is None:
            LOGGER.warning("Disponibilite demandee pour un livre inconnu : %s", bid)
            return 0
        n = 0
        for x in self.loans:
            if x["book"] == bid and x["returned"] == "":
                n = n + 1
        return bk["copies"] - n

    def borrow(self, member_id, book_id):
        member = self.find_member(member_id)
        if member is None:
            print("Erreur : membre inconnu")
            return False
        book = self.find_book(book_id)
        if book is None:
            print("Erreur : livre inconnu")
            return False
        reason = self.refusal_reason(member, book)
        if reason is not None:
            print("Refus : " + reason)
            return False
        self.create_loan(member, book)
        return True

    def refusal_reason(self, member, book):
        """Return the first refusal, in the established business priority order."""
        if not member["active"]:
            return "membre inactif"
        if self.has_overdue_loan(member["id"]):
            return "emprunts en retard"
        limit = LOAN_LIMITS.get(member["type"], DEFAULT_MAX_LOANS)
        if self.active_loan_count(member["id"]) >= limit:
            return f"limite d'emprunts atteinte ({limit})"
        if self.is_borrowing(member["id"], book["id"]):
            return "deja emprunte par ce membre"
        if self.available_copies(book["id"]) <= 0:
            return "plus d'exemplaire disponible"
        return None

    def has_overdue_loan(self, member_id):
        return any(
            loan["member"] == member_id
            and loan["returned"] == ""
            and parse_date(loan["due"]) < get_today()
            for loan in self.loans
        )

    def is_borrowing(self, member_id, book_id):
        return any(
            loan["member"] == member_id
            and loan["book"] == book_id
            and loan["returned"] == ""
            for loan in self.loans
        )

    def create_loan(self, member, book):
        """Persist and announce a loan after the refusal checks have passed."""
        today = get_today()
        due = today + timedelta(days=LOAN_DAYS.get(book["kind"], DEFAULT_LOAN_DAYS))
        new_id = self.next_loan_id()
        self.loans.append(
            {
                "id": new_id,
                "member": member["id"],
                "book": book["id"],
                "start": str(today),
                "due": str(due),
                "returned": "",
                "fee": 0,
            }
        )
        self.save()
        print(
            "Emprunt "
            + new_id
            + " enregistre : "
            + book["title"]
            + " pour "
            + member["name"]
            + ", retour avant le "
            + str(due)
        )

    # retour d'un document
    def return_loan(self, lid):
        ln = self.find_loan(lid)
        if ln is None:
            print("Erreur : emprunt inconnu")
            return
        if ln["returned"] != "":
            print("Erreur : emprunt deja rendu")
            return
        parties = self.loan_parties(ln)
        if parties is None:
            return
        bk, mb = parties
        t = get_today()
        d = (t - parse_date(ln["due"])).days
        f = late_fee(d, bk["kind"], mb["type"], bk["price"])
        d = max(d, 0)
        ln["returned"] = str(t)
        ln["fee"] = f
        self.save()
        print(
            "Retour enregistre : "
            + bk["title"]
            + ". Retard : "
            + str(d)
            + " jour(s). Penalite : "
            + "%.2f" % f
            + " EUR"
        )

    def find_overdue_loans(self) -> list[OverdueLoan]:
        """Calculate reminders without printing; log inconsistent references."""
        today = get_today()
        results = []
        for loan in sorted(self.loans, key=lambda item: (item["due"], item["id"])):
            if loan["returned"] != "":
                continue
            due = parse_date(loan["due"])
            if due >= today:
                continue
            parties = self.loan_parties(loan)
            if parties is None:
                continue
            book, member = parties
            days = (today - due).days
            fee = late_fee(days, book["kind"], member["type"], book["price"])
            results.append(OverdueLoan(loan["id"], member, book, days, fee))
        return results

    def overdue(self):
        overdue_loans = self.find_overdue_loans()
        if not overdue_loans:
            print("Aucun retard.")
            return
        for loan in overdue_loans:
            print(
                f"{loan.loan_id} | {loan.member['name']} | {loan.book['title']} | "
                f"{loan.days_late} jour(s) | {loan.fee:.2f} EUR"
            )
            # Simulation du rappel : aucun message n'est envoye.
            print(
                f"EMAIL -> {loan.member['email']} : Rappel, vous devez rendre "
                f"'{loan.book['title']}' (retard {loan.days_late} jours)"
            )
        total = sum(loan.fee for loan in overdue_loans)
        print(f"Total des penalites en cours : {total:.2f} EUR")

    def valid_loans(self):
        """Return loans with existing books and members, logging invalid ones."""
        loans = []
        for loan in self.loans:
            parties = self.loan_parties(loan)
            if parties is not None:
                loans.append((loan, *parties))
        return loans

    def loan_statistics(self, loans):
        ongoing = overdue = collected = pending = 0
        for loan, book, member in loans:
            if loan["returned"] != "":
                collected += loan["fee"]
                continue
            ongoing += 1
            days = (get_today() - parse_date(loan["due"])).days
            if days > 0:
                overdue += 1
                pending += late_fee(days, book["kind"], member["type"], book["price"])
        return ongoing, overdue, collected, pending

    def print_loan_rankings(self, loans):
        by_kind = {}
        by_book = {}
        titles = {}
        for loan, book, _member in loans:
            kind = book["kind"]
            by_kind[kind] = by_kind.get(kind, 0) + 1
            book_id = loan["book"]
            by_book[book_id] = by_book.get(book_id, 0) + 1
            titles[book_id] = book["title"]
        for kind in sorted(by_kind):
            print("  - " + kind + " : " + str(by_kind[kind]) + " emprunt(s)")
        ranking = sorted(
            (-count, titles[book_id]) for book_id, count in by_book.items()
        )
        print("Top 3 :")
        for position, (negative_count, title) in enumerate(ranking[:3], start=1):
            print(f"  {position}. {title} ({-negative_count})")

    def report(self):
        loans = self.valid_loans()
        ongoing, overdue, collected, pending = self.loan_statistics(loans)
        copies = sum(book["copies"] for book in self.books)
        active_members = sum(bool(member["active"]) for member in self.members)
        print("=== RAPPORT BIBLIOTECH ===")
        print("Date : " + str(get_today()))
        print(f"Titres : {len(self.books)} ({copies} exemplaires)")
        print(f"Membres : {len(self.members)} dont {active_members} actifs")
        print(
            f"Emprunts : {len(self.loans)} au total, {ongoing} en cours, "
            f"{overdue} en retard"
        )
        print("Penalites encaissees : " + "%.2f" % collected + " EUR")
        print("Penalites en attente : " + "%.2f" % pending + " EUR")
        self.print_loan_rankings(loans)

    def export(self, fname, sep):
        with open(fname, "w", encoding="utf-8") as f:
            f.write(
                "loan_id"
                + sep
                + "member"
                + sep
                + "title"
                + sep
                + "start"
                + sep
                + "due"
                + sep
                + "returned"
                + sep
                + "days_late"
                + sep
                + "fee\n"
            )
            n = 0
            for x in self.loans:
                parties = self.loan_parties(x)
                if parties is None:
                    continue
                bk, mb = parties
                end = parse_date(x["returned"]) if x["returned"] != "" else get_today()
                dl = (end - parse_date(x["due"])).days
                fee = late_fee(dl, bk["kind"], mb["type"], bk["price"])
                dl = max(dl, 0)
                f.write(
                    x["id"]
                    + sep
                    + mb["name"]
                    + sep
                    + bk["title"]
                    + sep
                    + x["start"]
                    + sep
                    + x["due"]
                    + sep
                    + x["returned"]
                    + sep
                    + str(dl)
                    + sep
                    + "%.2f" % fee
                    + "\n"
                )
                n = n + 1
        print("Export termine : " + str(n) + " lignes dans " + fname)

    # systeme de plugins (pour plus tard)
    def register_plugin(self, name, fn, priority=0, options=None):
        if options is None:
            options = {}
        self.plugins[name] = {"fn": fn, "priority": priority, "options": options}

    def run_plugins(self, event, payload=None):
        res = []
        for name in sorted(self.plugins, key=lambda n: self.plugins[n]["priority"]):
            try:
                res.append(
                    self.plugins[name]["fn"](
                        event, payload, **self.plugins[name]["options"]
                    )
                )
            except Exception:
                LOGGER.exception("Erreur dans le plugin %s (evenement %s)", name, event)
        return res


def get_today():
    if TODAY is None:
        return date.today()
    return TODAY


def list_command(library, args):
    for book in library.books:
        available = library.available_copies(book["id"])
        print(
            f"{book['id']} | {book['title']} | {book['author']} | {book['kind']} | "
            f"{available}/{book['copies']} disponible(s)"
        )
    return 0


def members_command(library, args):
    for member in library.members:
        status = "actif" if member["active"] else "inactif"
        print(
            f"{member['id']} | {member['name']} | {member['type']} | {status} | "
            f"{library.active_loan_count(member['id'])} emprunt(s) en cours"
        )
    return 0


def borrow_command(library, args):
    if len(args) < 3:
        print("Usage : borrow <id_membre> <id_document>")
        return 1
    return 0 if library.borrow(args[1], args[2]) else 2


def return_command(library, args):
    if len(args) < 2:
        print("Usage : return <id_emprunt>")
        return 1
    library.return_loan(args[1])
    return 0


def overdue_command(library, args):
    library.overdue()
    return 0


def report_command(library, args):
    library.report()
    return 0


def export_command(library, args):
    if len(args) < 2:
        print("Usage : export <fichier.csv>")
        return 1
    library.export(args[1], ";")
    return 0


COMMAND_HANDLERS = {
    "list": list_command,
    "members": members_command,
    "borrow": borrow_command,
    "return": return_command,
    "overdue": overdue_command,
    "report": report_command,
    "export": export_command,
}


def process(args):
    library = Library()
    if not args:
        print(
            "Usage : python bibliotech.py <commande> [arguments] [--today AAAA-MM-JJ]"
        )
        print("Commandes : list, members, borrow, return, overdue, report, export")
        return 1
    handler = COMMAND_HANDLERS.get(args[0])
    if handler is None:
        print("Commande inconnue : " + args[0])
        return 1
    return handler(library, args)


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--today" in a:
        i = a.index("--today")
        TODAY = parse_date(a[i + 1])
        a = a[:i] + a[i + 2 :]
    if "--debug" in a:
        debug = True
        a.remove("--debug")
    sys.exit(process(a))
