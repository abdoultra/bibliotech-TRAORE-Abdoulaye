# Synthèse TP1

## État initial

- 21 tests passent.
- 55 problèmes signalés par Ruff.

| Défaut                                             | Emplacement            | Correction                                                                            | Principe                             |
| -------------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------- | ------------------------------------ |
| Imports groupés, import global et import inutilisé | bibliotech.py, imports | Séparer os et sys, importer explicitement date, datetime et timedelta, supprimer json | Lisibilité et dépendances explicites |
| Comparaisons avec None par égalité | bibliotech.py, do_stuff(), ret(), get_today() | Utiliser is None et is not None | Comparaison explicite de l'absence de valeur |
