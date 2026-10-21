# Synthèse TP1

## État initial

- 21 tests passent.
- 55 problèmes signalés par Ruff.

| Défaut                                             | Emplacement            | Correction                                                                            | Principe                             |
| -------------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------- | ------------------------------------ |
| Imports groupés, import global et import inutilisé | bibliotech.py, imports | Séparer os et sys, importer explicitement date, datetime et timedelta, supprimer json | Lisibilité et dépendances explicites |
