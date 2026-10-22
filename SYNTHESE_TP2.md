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

## Niveau 1 : contrat de penalite

- Ajout de 13 cas parametres dans `tests/test_rules.py`, avant implementation.
- Rouge attendu observe : ImportError pour `late_fee` absente ; les 21 tests
  de caracterisation passent toujours lorsqu'ils sont executes separement.
- Cas couverts : absence de retard, retard negatif, trois tarifs, reduction
  etudiant, premium, plafond, document et membre inconnus, arrondi.
- Introduction de `late_fee(days_late, kind, member_type, price)` avec types,
  tarif de repli et reductions nommes. `calc_fee` est devenu un adaptateur
  temporaire : aucune deuxieme implementation du calcul n'a ete introduite.
- Migration de return_loan, overdue, loan_statistics (rapport) et export,
  avec un commit et les 48 tests verts apres chaque migration.
- Suppression de l'adaptateur devenu inutile. Les bornages des jours a zero
  dans return_loan et export sont conserves pour preserver les affichages.

## Niveau 2 : regles et clauses de garde

- Ajout de `tests/conftest.py` : donnees temporaires, date au 21 octobre 2026.
- Ajout de 11 cas dans `tests/test_borrow.py`, verts avant le refactoring :
  six refus avec verification d'absence de modification des donnees,
  limite, emprunt accepte et persiste, trois priorites de verification.
- Extract Function : `refusal_reason`, `has_overdue_loan`, `is_borrowing`
  et `create_loan`. `borrow` orchestre les recherches, le refus et la creation.
- Les messages et l'ordre des controles restent identiques.
- Ajout des constantes `DEFAULT_LOAN_DAYS` et `DEFAULT_MAX_LOANS` ;
  les dictionnaires de durees et de limites existaient deja depuis le TP1.

## Mesures finales

Commande : `python -m radon cc -s -a bibliotech.py` (Radon 6.0.1).

| Element | Debut TP2 | Fin des niveaux obligatoires |
| --- | --- | --- |
| borrow | C (13) | A (4) |
| refusal_reason | Incluse dans borrow | B (6) |
| has_overdue_loan | Incluse dans borrow | A (4) |
| is_borrowing | Incluse dans borrow | A (4) |
| create_loan | Incluse dans borrow | A (1) |
| report | A (3) | A (3) |
| overdue | B (7) | B (7) |
| Calcul des penalites | calc_fee A (4) | late_fee A (2) |
| Complexite moyenne | A (3.375), 32 blocs | A (3.111), 36 blocs |
| Fonctions en D ou pire | 0 | 0 |
| Tests | 35 | 59 |
| Signalements Ruff | 0 | 0 |

`refusal_reason` est B (6) : c'est une liste plate de cinq regles ordonnees,
testees une a une ; les tests d'emprunt couvrent les motifs et leur priorite.
Les quatre valeurs des methodes extraites ont ete mesurees avec Radon 6.0.1.

Les 21 tests de caracterisation et les references golden restent inchanges.
Les 14 cas de robustesse du TP1 passent egalement. Les donnees de reference
ne sont pas modifiees. Les 24 nouveaux cas portent le total a 59 tests.

## Corrections apres revue du TP2

- Ajout des mesures reelles des quatre methodes extraites au tableau ci-dessus.
- Le golden `return_on_time` couvre deja le retour L006 sans retard :
  affichage et CSV contiennent `0.00`. Aucun golden existant ne rend L005,
  l'emprunt premium ; overdue/export couvrent son calcul mais pas son retour.
- Ajout de `tests/test_returns.py` : deux scenarios de regression comparent
  exactement stdout et la ligne CSV ecrite, pour L006 (a temps) et L005
  (premium, dix jours de retard). Les fichiers golden d'origine restent intacts.
- Le passage interne de 0 entier a 0.0 flottant ne change pas ces sorties :
  return_loan et save formatent tous deux les penalites avec `%.2f`.
- La fixture documente maintenant l'etat des CSV necessaire aux tests
  d'emprunt et de retour, ainsi que l'isolation par copie temporaire.
- Total apres cette revue : 61 tests (les 59 precedents et 2 retours).

## Reste a faire pour le rendu

- Pousser la branche et ouvrir une PR vers main.
- Joindre le plan, les refactorings, les tests et les mesures a sa description.
- Organiser la revue croisee avec le groupe designe par l'enseignant,
  puis repondre a ses commentaires.
- Attendre la validation de l'enseignant avant fusion.
- Les bonus du niveau 3 ne sont pas entrepris.
