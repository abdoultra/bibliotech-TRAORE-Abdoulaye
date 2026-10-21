# Synthèse TP1

## État initial

- 21 tests passent.
- 55 problèmes signalés par Ruff.

| Défaut                                             | Emplacement            | Correction                                                                            | Principe                             |
| -------------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------- | ------------------------------------ |
| Imports groupés, import global et import inutilisé | bibliotech.py, imports | Séparer os et sys, importer explicitement date, datetime et timedelta, supprimer json | Lisibilité et dépendances explicites |
| Comparaisons avec None par égalité | bibliotech.py, do_stuff(), ret(), get_today() | Utiliser is None et is not None | Comparaison explicite de l'absence de valeur |
| Comparaisons explicites à True et False | bibliotech.py, load(), do_stuff(), report(), process() | Tester directement les booléens et utiliser not pour leur négation | Lisibilité des conditions |
| Fermeture manuelle des fichiers | bibliotech.py, load(), save(), export() | Utiliser with open(...) as f pour les cinq ouvertures | Gestion automatique des ressources, même en cas d'exception |

## Corrections apres relecture de l'enseignant

| Defaut | Emplacement | Correction | Principe |
| --- | --- | --- | --- |
| Execution du prix CSV par eval | load | Conversion par float | Securite |
| Penalites dupliquees quatre fois | ret, overdue, report, export | Fonction calc_fee et tarifs DAILY_FEES communs, reductions et plafond conserves | DRY |
| Huit niveaux de conditions et nom vague | do_stuff | Renommage borrow, refus anticipes dans le meme ordre, constantes de durees et limites | Lisibilite |
| Erreurs de plugins masquees | run_plugins | Exception journalisee avec nom du plugin et trace, poursuite des autres plugins | Observabilite |
| Dictionnaire par defaut partage | register_plugin | options=None et dictionnaire neuf pour chaque appel | Isolation des etats |
| References orphelines | loan_parties, ret, report, overdue, export, dispo | Ignorer et signaler les emprunts incoherents ; disponibilite inconnue a zero | Robustesse |
| Identifiant mal forme | next_loan_id | Valider le format L suivi de chiffres avant conversion ; signaler les autres | Validation |
| Encodage implicite | load, save, export | encoding="utf-8" explicite | Portabilite |
| Code mort et masquage d'un nom Python | old_calc_fee, cache, global TODAY, find | Supprimer le code inutilise et renommer id en item_id | Maintenabilite |
| Rappels ambigus | overdue, README | Documenter explicitement la simulation EMAIL sans envoi reel | Clarte du contrat |

Les fichiers du dossier tests/ restent inchanges.

### Validation apres relecture

- 21 tests de caracterisation passent.
- Ruff : 3 signalements C901 restants (load, report, process), contre 55 au depart.
- Verifications ciblees executees sur copies temporaires : tarifs et reductions,
  plafond, jours negatifs, references supprimees, identifiants invalides, accents
  UTF-8, isolation des options, journalisation des erreurs et poursuite des plugins,
  rejet d'un prix contenant du code Python sans execution.
- Aucun fichier de tests/ ou data/ modifie.
