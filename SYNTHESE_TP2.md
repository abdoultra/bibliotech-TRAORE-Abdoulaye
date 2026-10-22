# TP2 : refactoring de BiblioTech

## Point de depart

- Branche : `tp2/refactoring`, creee depuis `main` au commit `80df362`
  (fusion du TP1).
- 35 tests passent : 21 tests de caracterisation et 14 cas de robustesse.
- `python -m ruff check .` : aucun signalement.
- Radon 6.0.1 : `borrow` C (13), `overdue` B (7), `report` A (3).
- Complexite moyenne : A (3.375), 32 blocs analyses.
- Aucune fonction en D ; l'objectif restant est notamment `borrow` en A.

## Adaptation du guide a notre TP1

Le calcul est deja centralise dans `calc_fee(days, book, member)`, et `borrow`
possede deja des clauses de garde. Ces changements ont ete demandes pendant
la relecture du TP1. On conserve cet historique et on complete les exigences
du TP2, sans reintroduire de duplication ni recreer artificiellement des commits.

## Plan obligatoire

1. Configurer `pythonpath` pour pytest et ajouter Radon aux dependances.
2. Ecrire les tests du contrat `late_fee` (temps, retard negatif, tarifs,
   reductions, plafond, arrondi et type inconnu), avant son implementation.
3. Introduire `late_fee(days_late, kind, member_type, price)`, puis migrer
   chaque appel existant en petits pas pour conserver un calcul unique.
4. Ajouter la fixture partagee et les tests des emprunts.
5. Extraire `refusal_reason`, `has_overdue_loan`, `is_borrowing` et
   `create_loan`, en conservant l'ordre des controles et les messages.
6. Mesurer a nouveau, ouvrir une PR vers main et organiser sa relecture.

Les bonus seront envisages apres les deux niveaux obligatoires.

## Etape 1 : configuration

- Ajout de `pythonpath = ["."]` dans la configuration pytest.
- Ajout et installation de `radon>=6.0`.
- Validation : 35 tests verts, Ruff sans signalement ; mesures ci-dessus.
