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
LOAN_DAYS = {"book": 21, "dvd": 7, "magazine": 3}
LOAN_LIMITS = {"student": 5, "premium": 8}


class Library:
    def __init__(self):
        self.b = []
        self.m = []
        self.l = []
        self.plugins = {}
        self.load()

    # chargement des donnees
    def load(self):
        with open(DATA + "/books.csv", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines[1:]:
            if line.strip() == "":
                continue
            x = line.strip().split(";")
            self.b.append(
                {
                    "id": x[0],
                    "title": x[1],
                    "author": x[2],
                    "kind": x[3],
                    "price": float(x[4]),
                    "copies": int(x[5]),
                }
            )
        with open(DATA + "/members.csv", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines[1:]:
            if line.strip() == "":
                continue
            x = line.strip().split(";")
            a = x[4] == "1"
            self.m.append(
                {"id": x[0], "name": x[1], "email": x[2], "type": x[3], "active": a}
            )
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
            self.l.append(
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
        if debug:
            print("chargement ok", len(self.b), len(self.m), len(self.l))

    def save(self):
        with open(DATA + "/loans.csv", "w", encoding="utf-8") as f:
            f.write("id;member_id;book_id;start;due;returned;fee\n")
            for x in self.l:
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
        collections = {"b": self.b, "m": self.m, "l": self.l}
        return next(
            (item for item in collections.get(category, []) if item["id"] == item_id),
            None,
        )

    def loan_parties(self, loan):
        """Ignore orphan loans with a diagnostic instead of crashing."""
        book = self.find("b", loan["book"])
        member = self.find("m", loan["member"])
        if book is None or member is None:
            LOGGER.warning(
                "Emprunt %s ignore : livre ou membre introuvable", loan["id"]
            )
            return None
        return book, member

    def next_loan_id(self):
        numbers = []
        for loan in self.l:
            match = re.fullmatch(r"L([0-9]+)", loan["id"])
            if match is None:
                LOGGER.warning("Identifiant d'emprunt invalide ignore : %s", loan["id"])
                continue
            numbers.append(int(match[1]))
        return f"L{max(numbers, default=0) + 1:03d}"

    def nb(self, mid):
        n = 0
        for x in self.l:
            if x["member"] == mid and x["returned"] == "":
                n = n + 1
        return n

    def dispo(self, bid):
        bk = self.find("b", bid)
        if bk is None:
            LOGGER.warning("Disponibilite demandee pour un livre inconnu : %s", bid)
            return 0
        n = 0
        for x in self.l:
            if x["book"] == bid and x["returned"] == "":
                n = n + 1
        return bk["copies"] - n

    def borrow(self, mid, bid):
        member = self.find("m", mid)
        if member is None:
            print("Erreur : membre inconnu")
            return False
        book = self.find("b", bid)
        if book is None:
            print("Erreur : livre inconnu")
            return False
        if not member["active"]:
            print("Refus : membre inactif")
            return False
        active_loans = [
            loan for loan in self.l if loan["member"] == mid and loan["returned"] == ""
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
        if self.dispo(bid) <= 0:
            print("Refus : plus d'exemplaire disponible")
            return False
        today = get_today()
        due = today + timedelta(days=LOAN_DAYS.get(book["kind"], 21))
        new_id = self.next_loan_id()
        self.l.append(
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
    def ret(self, lid):
        ln = self.find("l", lid)
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
        tmp = []
        for x in self.l:
            if self.loan_parties(x) is None:
                continue
            if (
                x["returned"] == ""
                and datetime.strptime(x["due"], "%Y-%m-%d").date() < get_today()
            ):
                tmp.append(x)
        if len(tmp) == 0:
            print("Aucun retard.")
            return
        tmp.sort(key=lambda x: (x["due"], x["id"]))
        total = 0
        for x in tmp:
            parties = self.loan_parties(x)
            if parties is None:
                continue
            book, member = parties
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

    def report(self):
        data2 = {}
        print("=== RAPPORT BIBLIOTECH ===")
        print("Date : " + str(get_today()))
        c = 0
        for x in self.b:
            c = c + x["copies"]
        print("Titres : " + str(len(self.b)) + " (" + str(c) + " exemplaires)")
        a = 0
        for x in self.m:
            if x["active"]:
                a = a + 1
        print("Membres : " + str(len(self.m)) + " dont " + str(a) + " actifs")
        en_cours = 0
        en_retard = 0
        encaisse = 0
        a_payer = 0
        for x in self.l:
            if self.loan_parties(x) is None:
                continue
            if x["returned"] == "":
                en_cours = en_cours + 1
                due = datetime.strptime(x["due"], "%Y-%m-%d").date()
                if due < get_today():
                    en_retard = en_retard + 1
                    bk = self.find("b", x["book"])
                    mb = self.find("m", x["member"])
                    j = (get_today() - due).days
                    a_payer = a_payer + calc_fee(j, bk, mb)
            else:
                encaisse = encaisse + x["fee"]
            if x["book"] in data2:
                data2[x["book"]] = data2[x["book"]] + 1
            else:
                data2[x["book"]] = 1
        print(
            "Emprunts : "
            + str(len(self.l))
            + " au total, "
            + str(en_cours)
            + " en cours, "
            + str(en_retard)
            + " en retard"
        )
        print("Penalites encaissees : " + "%.2f" % encaisse + " EUR")
        print("Penalites en attente : " + "%.2f" % a_payer + " EUR")
        # par type
        k = {}
        for x in self.l:
            if self.loan_parties(x) is None:
                continue
            bk = self.find("b", x["book"])
            if bk["kind"] in k:
                k[bk["kind"]] += 1
            else:
                k[bk["kind"]] = 1
        for kk in sorted(k.keys()):
            print("  - " + kk + " : " + str(k[kk]) + " emprunt(s)")
        # top 3
        lst = []
        for key in data2:
            lst.append((-data2[key], self.find("b", key)["title"]))
        lst.sort()
        print("Top 3 :")
        i = 0
        for x in lst:
            if i < 3:
                print("  " + str(i + 1) + ". " + x[1] + " (" + str(-x[0]) + ")")
            i = i + 1

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
            for x in self.l:
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
    """Calculate the rounded fee, with membership reduction and price cap."""
    if days <= 0:
        return 0
    fee = days * DAILY_FEES.get(book["kind"], DAILY_FEES["book"])
    if member["type"] == "student":
        fee *= 0.5
    elif member["type"] == "premium":
        fee = 0
    return round(min(fee, book["price"]), 2)


def process(args):
    lib = Library()
    if len(args) == 0:
        print(
            "Usage : python bibliotech.py <commande> [arguments] [--today AAAA-MM-JJ]"
        )
        print("Commandes : list, members, borrow, return, overdue, report, export")
        return 1
    cmd = args[0]
    if cmd == "list":
        for x in lib.b:
            n = lib.dispo(x["id"])
            print(
                x["id"]
                + " | "
                + x["title"]
                + " | "
                + x["author"]
                + " | "
                + x["kind"]
                + " | "
                + str(n)
                + "/"
                + str(x["copies"])
                + " disponible(s)"
            )
    elif cmd == "members":
        for x in lib.m:
            s = "actif" if x["active"] else "inactif"
            print(
                x["id"]
                + " | "
                + x["name"]
                + " | "
                + x["type"]
                + " | "
                + s
                + " | "
                + str(lib.nb(x["id"]))
                + " emprunt(s) en cours"
            )
    elif cmd == "borrow":
        if len(args) < 3:
            print("Usage : borrow <id_membre> <id_document>")
            return 1
        r = lib.borrow(args[1], args[2])
        if not r:
            return 2
    elif cmd == "return":
        if len(args) < 2:
            print("Usage : return <id_emprunt>")
            return 1
        lib.ret(args[1])
    elif cmd == "overdue":
        lib.overdue()
    elif cmd == "report":
        lib.report()
    elif cmd == "export":
        if len(args) < 2:
            print("Usage : export <fichier.csv>")
            return 1
        lib.export(args[1], ";")
    else:
        print("Commande inconnue : " + cmd)
        return 1
    return 0


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
