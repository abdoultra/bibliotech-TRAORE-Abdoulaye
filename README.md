# BiblioTech

## 1. Présentation

BiblioTech est une application Python en ligne de commande de gestion d'une
bibliothèque municipale. Elle affiche le catalogue et les membres, enregistre
les emprunts et retours, calcule les pénalités, produit les retards, un rapport
et un export CSV. Projet individuel d'Abdoulaye Traoré, Master 1 Informatique.

Les rappels `EMAIL ->` sont une **simulation** : aucun courriel n'est envoyé.
Les scénarios habituels conservent les sorties de référence des 21 tests fournis.
Les corrections de robustesse ajoutent un traitement explicite des données
incohérentes sans modifier ces références.

### Organisation

- `bibliotech.py` : point d'entrée CLI, règles métier et classe `Library`.
- `data/books.csv`, `members.csv`, `loans.csv` : données UTF-8, séparateur `;`.
- `tests/test_caracterisation.py`, `tests/golden/` : références d'origine intactes.
- `tests/test_rules.py`, `test_borrow.py`, `test_returns.py` : règles et sorties.
- `tests/test_robustesse.py` : données incohérentes, plugins et sécurité des prix.
- `tests/test_dates.py`, `test_lookup.py`, `test_overdue.py` : ajouts du TP3.
- `tests/conftest.py` : copie temporaire des CSV et date fixe pour les tests métier.
- `SYNTHESE_TP1.md`, `SYNTHESE_TP2.md`, `SYNTHESE_TP3.md` : étapes et décisions.
- `docs/audit_avant.txt`, `docs/audit_apres.txt` : sorties des mesures comparables.

### Règles métier conservées

| Règle | Valeurs |
| --- | --- |
| Durée d'emprunt | livre 21 jours, DVD 7 jours, magazine 3 jours, autre 21 jours |
| Limite simultanée | standard 3, étudiant 5, premium 8 |
| Pénalité quotidienne | livre 0,50 €, DVD 1 €, magazine 0,20 €, autre 0,50 € |
| Réduction | étudiant 50 %, premium 100 %, autre 0 % |
| Plafond | prix du document, puis arrondi au centime |

Les refus suivent l'ordre : membre inactif, emprunt en retard, limite atteinte,
document déjà emprunté, absence d'exemplaire disponible. Les recherches de
membre et document inconnus précèdent ces règles.

## 2. TP 1 - Clean Code

Le point initial `v0-initial` avait 21 tests verts et 55 signalements avec la
configuration Ruff du TP1. Le nettoyage a porté sur les imports explicites,
les noms, les comparaisons et les ressources. Exemples :

```python
# Booléen réel : intention plus lisible.
if not late:
    ...

# None représente l'absence d'un résultat de recherche.
if member is None:
    return False

# Fermeture garantie à la sortie du bloc, même sur exception.
with open(path, encoding="utf-8") as file:
    lines = file.readlines()
```

La relecture a élargi le travail : `eval` est devenu `float` pour convertir les
prix sans exécuter une expression issue du CSV. Les erreurs de plugins sont
journalisées avec leur trace et les options par défaut utilisent `None`, pour
éviter un dictionnaire mutable partagé. Les noms `books`, `members`, `loans`,
`return_loan`, `active_loan_count` et `available_copies` expriment leur rôle.

Les emprunts orphelins sont ignorés dans les calculs concernés avec un
avertissement ; un retour orphelin ne modifie pas les données. La disponibilité
d'un livre inconnu vaut zéro. Les identifiants hors du format `L` suivi de chiffres
sont signalés et exclus du calcul du prochain numéro. Les 14 tests de robustesse
rendent ces contrôles rejouables. Fin TP1 : 35 tests verts, zéro signalement Ruff
avec les règles alors configurées.

[PR TP1 et échanges de revue](https://github.com/abdoultra/bibliotech-TRAORE-Abdoulaye/pull/1).

## 3. TP 2 - Refactoring

Le calcul avait déjà été centralisé en `calc_fee` pendant la revue du TP1.
Le TP2 l'a adapté au contrat pur et typé `late_fee`, sans réintroduire de copies :

```python
late_fee(10, "dvd", "student", 14.99)  # 5,00 €
```

Les tarifs et réductions sont des dictionnaires nommés. Une clause de garde
renvoie 0.0 sans retard, `min` applique le plafond et `round` l'arrondi.
Treize cas paramétrés précèdent l'implémentation : rouge d'import attendu,
puis passage au vert. Un adaptateur temporaire a permis de migrer un appel
par commit dans le retour, les retards, le rapport et l'export, avant suppression.
Les jours affichés restent bornés à zéro pour les retours en avance.

`borrow` délègue désormais les règles à `refusal_reason`, les recherches de
retard et de doublon à `has_overdue_loan` et `is_borrowing`, puis la persistance
à `create_loan`. Les 11 tests d'emprunt ont été écrits avant le découpage.
Ils vérifient les refus, certaines priorités et la sauvegarde d'un emprunt accepté.

| Méthode | Radon à la fin du TP2 |
| --- | --- |
| borrow | A (4), contre C (13) au début du TP2 |
| refusal_reason | B (6) |
| has_overdue_loan | A (4) |
| is_borrowing | A (4) |
| create_loan | A (1) |

Le B (6) de `refusal_reason` correspond à cinq règles plates, ordonnées et testées.
Les décisions métier existent toujours : le découpage les rend plus lisibles.
La dernière revue a ajouté deux tests exacts de retour à temps et premium :
le passage interne de 0 à 0.0 conserve `0.00` dans le message et le CSV grâce
au format à deux décimales. La fixture documente les hypothèses sur les CSV.
Fin TP2 : 61 tests verts, sans modification des goldens.

[PR TP2 et historique des petits pas](https://github.com/abdoultra/bibliotech-TRAORE-Abdoulaye/pull/2).

## 4. TP 3 - Qualité

### Analyse initiale et priorités

Le tag immobile `v2-fin-j2` désigne `f6eda6b`, fusion du TP2. Les 61 tests ont
été vérifiés sur main avant sa création. La branche de travail est `qualite`.
L'audit fixe les familles Ruff, exclut les tests de la mesure de production et
utilise exactement les mêmes commandes avant et après (partie 6).

Les exemples du guide tels que `eval` et les arguments mutables étaient déjà
corrigés. L'audit sécurité de production relève donc zéro signalement au départ.
La lecture du code révèle cependant des améliorations utiles :

| Priorité | Défaut et preuve | Amélioration et justification |
| --- | --- | --- |
| 1 | Conversion de dates répétée, recherche de strptime | Extract Function : parse_date centralise le format et conserve ValueError |
| 2 | find sélectionne une collection selon une chaîne | Remove Flag Argument : find_book, find_member, find_loan appellent find_by_id |
| 3 | overdue B (7) sélectionne, calcule et affiche | Split Phase : find_overdue_loans renvoie des OverdueLoan, overdue affiche |
| 4 | Famille S absente des règles par défaut | Ajouter S à la configuration pour pérenniser l'audit sécurité |

Chaque changement a son commit après les tests. Aucun `noqa` n'a été ajouté et
le seuil Ruff de complexité reste 8. Les règles existantes I et N sont conservées.
Les assertions des tests ont une exception S101. S603 est ignorée uniquement
pour les trois fichiers lançant la CLI : interpréteur et script absolus, arguments
internes aux tests, sans shell. Ces exceptions sont justifiées dans pyproject.toml,
ne concernent pas la production et ne modifient pas le test fourni.

### Tests ajoutés

- 7 cas de dates : date courante de référence, année bissextile, début d'année,
  mois invalide, jour invalide, autre format et chaîne vide.
- 5 cas de recherche : premier résultat, absence et isolation des trois collections.
- 4 cas de retards : données ordonnées et pénalités, absence de retards, échéance
  aujourd'hui/rendu, référence orpheline signalée une fois.

`find_overdue_loans` ne produit pas de sortie standard. Les références invalides
restent journalisées. Elle calcule la date du jour une seule fois et la date
d'échéance une fois par emprunt actif. Au 21/10/2026, les retards valides sont
L003, L004, L005 et L007 pour 7,50 €, 6,50 €, 0,00 € et 0,30 €.

### Comparaison avant/après

Mesures Radon 6.0.1 et Ruff 0.17.1. Le relevé initial a aussi été reproduit sur
une extraction temporaire du tag, avec les mêmes outils et commandes.
Les sorties brutes se trouvent dans `docs/audit_avant.txt` et `docs/audit_apres.txt`.

| Indicateur | Avant : v2-fin-j2 | Après : qualite |
| --- | --- | --- |
| Signalements Ruff, production, familles imposées | 0 | 0 |
| Complexité moyenne Radon | A (3,111111), 36 blocs | A (2,833333), 42 blocs |
| Pire fonction | overdue B (7) | refusal_reason B (6) |
| Fonctions notées C ou pire | 0 | 0 |
| Tests, tous verts | 61 | 77 |
| Indice de maintenabilité bibliotech.py | B (12,70) | B (11,44) |

La sécurité statique était déjà sans signalement : le résultat reste zéro avec
le même périmètre. La configuration rend ce contrôle régulier. Le gain est aussi
la testabilité : 16 cas supplémentaires couvrent les nouveaux contrats.
`overdue` passe de B (7) à A (4), sa méthode extraite `find_overdue_loans` est A (5).
Les fonctions `parse_date`, `find_book`, `find_member` et `find_loan` sont A (1),
et `find_by_id` est A (3). La classe de données `OverdueLoan` est A (1).

La moyenne baisse, mais son nombre de blocs augmente : elle doit se lire avec
les valeurs individuelles. **L'indice de maintenabilité recule**, de 12,70 à 11,44.
Cet indicateur composite dépend notamment de la taille, de la complexité et des
commentaires. Les extractions ajoutent des éléments explicites au fichier et le
score ne traduit pas une amélioration sur tous les axes. La classe Library reste
chargée. On conserve ce résultat défavorable et on propose un découpage ultérieur
en modules plutôt que d'ajouter des commentaires artificiels pour améliorer le score.

### Dette restante et périmètre

- Library contient encore stockage, règles et rapports : extraire des modules
  cohérents nécessiterait un chantier testé séparément.
- La date, le chemin des données et le mode debug sont globaux. Une injection
  de configuration et d'horloge faciliterait l'usage simultané de bibliothèques.
- Les dictionnaires métier restent peu typés. La dataclass OverdueLoan est figée
  en surface, mais les dictionnaires livre/membre qu'elle référence restent mutables.
- float et round conservent l'arrondi du projet. Les prix négatifs/non finis,
  dates de données corrompues, doublons et transactions d'écriture restent à définir.
- Les orphelins sont signalés sans réparation. Le total historique du rapport
  compte les lignes, tandis que ses calculs ignorent les références invalides.
- Les fixtures utilisent le jeu CSV documenté. Les tests ne couvrent pas tous les cas.
- Les rappels e-mail restent simulés. Aucun système d'envoi n'est configuré.

Le niveau 2 utilise les outils du cours : configuration Ruff, indice de
maintenabilité et contrôle du format. Aucun nouvel outil bonus, service
SonarQube, hook pre-commit ou action GitHub n'a été ajouté dans ce TP.

## 5. Bilan des trois jours

Le TP1 a rendu les intentions explicites et a transformé des remarques de revue
en contrôles de robustesse. Le TP2 a renforcé les règles par des tests directs
et des transformations courtes. Le TP3 complète l'audit et documente les compromis.

Les difficultés importantes ont été l'ordre des refus, les jours négatifs lors
d'une extraction, le format exact de la pénalité nulle et les hypothèses sur les
CSV. Les tests protègent les cas écrits, sans prouver l'absence de défauts.
Ruff vérifie des règles statiques, Radon mesure une structure, et la revue
complète ces preuves par une lecture humaine.

Le travail a utilisé une assistance IA pour la rédaction, les modifications et
les vérifications. Les choix et limites doivent pouvoir être expliqués par
l'auteur. La suite la plus utile serait une séparation stockage/règles/rapports
et une validation explicite des données d'entrée, avec tests avant modification.

## 6. Exécution du projet

Python 3.10 ou plus récent et Git sont nécessaires. Depuis un terminal neuf :

```bash
git clone https://github.com/abdoultra/bibliotech-TRAORE-Abdoulaye.git
cd bibliotech-TRAORE-Abdoulaye
git switch qualite
python -m venv .venv
```

Activation selon le terminal :

```bash
# Git Bash sous Windows
source .venv/Scripts/activate

# Linux/macOS
source .venv/bin/activate
```

Sous PowerShell Windows :

```powershell
.\.venv\Scripts\Activate.ps1
```

Après activation, les mêmes commandes Python fonctionnent dans les trois cas :

```bash
python -m pip install -r requirements.txt
python bibliotech.py list
python bibliotech.py members
python bibliotech.py overdue --today 2026-10-21
python bibliotech.py report --today 2026-10-21
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

Les tests métier utilisent leurs propres copies temporaires et une date fixe.
La CLI sans `--today` utilise la date réelle. Exemple d'export :

```bash
python bibliotech.py export emprunts.csv --today 2026-10-21
```

Les commandes ci-dessous **modifient data/loans.csv**. Elles sont des exemples
d'utilisation, pas une étape nécessaire aux mesures :

```bash
python bibliotech.py borrow M005 B005 --today 2026-10-21
python bibliotech.py return L004 --today 2026-10-21
```

Audit comparable TP3, à exécuter exactement de la même manière avant et après :

```bash
python -m ruff check . --select E,W,F,B,S,C90,SIM --extend-exclude tests --statistics
python -m radon cc -s -a --exclude "tests/*" .
python -m radon cc -s -n C --exclude "tests/*" .
python -m pytest -q
python -m radon mi -s --exclude "tests/*" .
```

Une sortie vide pour le premier contrôle signifie zéro signalement ; pour le
filtre Radon C, elle signifie aucune fonction C ou pire. Les tests sont exclus
de la mesure de production, mais sont exécutés par pytest et contrôlés par
`ruff check .` avec les exceptions précises documentées plus haut.

```bash
git log --oneline v2-fin-j2..qualite
git diff --stat v2-fin-j2..qualite
```

Le tag `v2-fin-j2` et la branche `qualite` sont publiés. La PR du TP3 doit être
ouverte vers main puis relue par l'enseignant, sans fusion préalable.
