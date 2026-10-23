# TP3 : audit et amélioration finale

## État initial

Référence : `v2-fin-j2`, commit `f6eda6b`, fusion du TP2 dans main.
Le tag a été créé après vérification des 61 tests sur main.

Commandes comparables avant et après, depuis la racine :

```bash
python -m ruff check . --select E,W,F,B,S,C90,SIM --extend-exclude tests --statistics
python -m radon cc -s -a --exclude "tests/*" .
python -m radon cc -s -n C --exclude "tests/*" .
python -m pytest -q
python -m radon mi -s --exclude "tests/*" .
```

| Indicateur | Avant |
| --- | --- |
| Signalements Ruff | 0 |
| Complexité moyenne | A (3.111111), 36 blocs |
| Pire fonction | Library.overdue B (7) |
| Fonctions C ou pire | 0 |
| Tests verts | 61 |
| Indice de maintenabilité | bibliotech.py B (12.70) |

## Lecture du code et priorités

Les exemples de failles du guide (eval, except nu, défaut mutable) sont déjà
corrigés depuis le TP1. Aucun défaut de sécurité n'est inventé pour l'audit.

| Défaut réel | Repérage | Catégorie | Priorité |
| --- | --- | --- | --- |
| Conversion ISO des dates répétée | Recherche des appels strptime | Duplication, validation | 1 |
| Sélection de collection par catégorie dans find | Lecture des appels et de la méthode | Interface et lisibilité | 2 |
| overdue mélange sélection, calcul et affichage | Lecture et Radon B (7) | Responsabilités, testabilité | 3 |
| Famille S absente de la configuration par défaut | pyproject.toml | Pérennité des contrôles | 4 |

Chaque transformation est précédée de tests ciblés et suivie de la suite
complète. Les 21 tests de caractérisation et les goldens restent intacts.
Le seuil de complexité Ruff de 8 est conservé.
