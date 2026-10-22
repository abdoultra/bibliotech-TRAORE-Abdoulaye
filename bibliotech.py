# BiblioTech v1.3
# gestion de la bibliotheque municipale
# auteur : stagiaire 2019, modifie par plusieurs personnes depuis

import logging
import os
import re
import sys
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


def late_fee(days_late: int, kind: str, member_type: str, price: float) -> float:
    """Return the discounted late fee, capped at the document price."""
    if days_late <= 0:
        return 0.0
    fee = days_late * DAILY_FEES.get(kind, DEFAULT_DAILY_FEE)
    fee *= 1 - DISCOUNTS.get(member_type, 0.0)
    return round(min(fee, price), 2)


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

    def find(self, category, item_id):
        collections = {"book": self.books, "member": self.members, "loan": self.loans}
        return next(
            (item for item in collections.get(category, []) if item["id"] == item_id),
            None,
        )

    def loan_parties(self, loan):
        """Ignore orphan loans with a diagnostic instead of crashing."""
        book = self.find("book", loan["book"])
        member = self.find("member", loan["member"])
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
        bk = self.find("book", bid)
        if bk is None:
            LOGGER.warning("Disponibilite demandee pour un livre inconnu : %s", bid)
            return 0
        n = 0
        for x in self.loans:
            if x["book"] == bid and x["returned"] == "":
                n = n + 1
        return bk["copies"] - n

    def borrow(self, mid, bid):
        member = self.find("member", mid)
        if member is None:
            print("Erreur : membre inconnu")
            return False
        book = self.find("book", bid)
        if book is None:
            print("Erreur : livre inconnu")
            return False
        if not member["active"]:
            print("Refus : membre inactif")
            return False
        active_loans = [
            loan
            for loan in self.loans
            if loan["member"] == mid and loan["returned"] == ""
        ]
        if any(
            datetime.strptime(loan["due"], "%Y-%m-%d").date() < get_today()
            for loan in active_loans
        ):
            print("Refus : emprunts en retard")
            return False
        limit = LOAN_LIMITS.get(member["type"], 3)
        if len(active_loans) >= limit:
            print("Refus : limite d'emprunts atteinte (" + str(limit) + ")")
            return False
        if any(loan["book"] == bid for loan in active_loans):
            print("Refus : deja emprunte par ce membre")
            return False
        if self.available_copies(bid) <= 0:
            print("Refus : plus d'exemplaire disponible")
            return False
        today = get_today()
        due = today + timedelta(days=LOAN_DAYS.get(book["kind"], 21))
        new_id = self.next_loan_id()
        self.loans.append(
            {
                "id": new_id,
                "member": mid,
                "book": bid,
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
        return True

    # retour d'un document
    def return_loan(self, lid):
        ln = self.find("loan", lid)
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
        d = (t - datetime.strptime(ln["due"], "%Y-%m-%d").date()).days
        f = calc_fee(d, bk, mb)
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

    # liste des retards + simulation des rappels
    def overdue(self):
        overdue_loans = []
        for loan in self.loans:
            if loan["returned"] != "":
                continue
            due = datetime.strptime(loan["due"], "%Y-%m-%d").date()
            if due >= get_today():
                continue
            parties = self.loan_parties(loan)
            if parties is not None:
                overdue_loans.append((loan, *parties))
        if not overdue_loans:
            print("Aucun retard.")
            return
        overdue_loans.sort(key=lambda item: (item[0]["due"], item[0]["id"]))
        total = 0
        for x, book, member in overdue_loans:
            nbj = (get_today() - datetime.strptime(x["due"], "%Y-%m-%d").date()).days
            p = calc_fee(nbj, book, member)
            total = total + p
            print(
                x["id"]
                + " | "
                + member["name"]
                + " | "
                + book["title"]
                + " | "
                + str(nbj)
                + " jour(s) | "
                + "%.2f" % p
                + " EUR"
            )
            # Simulation du rappel : aucun message n'est envoye.
            print(
                "EMAIL -> "
                + member["email"]
                + " : Rappel, vous devez rendre '"
                + book["title"]
                + "' (retard "
                + str(nbj)
                + " jours)"
            )
        print("Total des penalites en cours : " + "%.2f" % total + " EUR")

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
            days = (
                get_today() - datetime.strptime(loan["due"], "%Y-%m-%d").date()
            ).days
            if days > 0:
                overdue += 1
                pending += calc_fee(days, book, member)
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
                if x["returned"] != "":
                    end = datetime.strptime(x["returned"], "%Y-%m-%d").date()
                else:
                    end = get_today()
                dl = (end - datetime.strptime(x["due"], "%Y-%m-%d").date()).days
                fee = calc_fee(dl, bk, mb)
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


def calc_fee(days, book, member):
    """Temporary adapter while callers migrate to the explicit late_fee contract."""
    return late_fee(days, book["kind"], member["type"], book["price"])


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
        TODAY = datetime.strptime(a[i + 1], "%Y-%m-%d").date()
        a = a[:i] + a[i + 2 :]
    if "--debug" in a:
        debug = True
        a.remove("--debug")
    sys.exit(process(a))
