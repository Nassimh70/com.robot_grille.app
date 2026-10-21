# Projet PA — Theme 2 : navigation d'un robot sur une grille

Projet académique : **recherche de chemin sur grille**, comparaison empirique
d'algorithmes et **interface graphique** interactive (3 niveaux de difficulté).

Tout le code est en Python 3.11+ et n'utilise **que la bibliothèque standard**
(`tkinter` pour l'interface). Aucune dépendance à installer, aucun fichier de
configuration : le projet fonctionne tel quel.

---

## 1. Lancer le projet

### Interface graphique

```bash
cd "D:\Projet PA Theme 2"
python -m src.app
```

### Benchmark (génère `RESULTATS.md`)

```bash
cd "D:\Projet PA Theme 2"
python -m src.benchmark
```

Le fichier `RESULTATS.md` est **écrit automatiquement** à la racine du projet :
il contient les mesures réelles (moyennes, médianes, écarts-types) et le
détail par configuration.

Options utiles :

| Option | Effet |
|---|---|
| `--quick` | campagne réduite (20×20 et 50×50, 10 répétitions) — essai rapide |
| `--reps N` | nombre de grilles aléatoires par combinaison (30 par défaut) |
| `--seed N` | graine du générateur aléatoire (reproductibilité) |
| `--output FICHIER` | chemin du rapport Markdown |
| `--no-replan` | saute l'expérience de replanification |

### Auto-contrôle du projet

```bash
cd "D:\Projet PA Theme 2"
python -m src.selfcheck
```

Vingt-et-une vérifications rejouent les **invariants de correctness** du
projet et affichent un rapport lisible (`ok` / `ECHEC`) ; le code de sortie
vaut `0` si tout passe. Parmi elles :

* **A\* retrouve exactement le même coût que Dijkstra** (critère
  d'admissibilité de l'heuristique) ;
* **D\* Lite retrouve le même chemin qu'A\*** après chaque modification de la
  carte, et replanifie plus vite ;
* l'anytime A\* converge vers l'optimum et respecte son budget ;
* la **règle anti-coins** est bien appliquée en 8-voisins ;
* BFS est optimal en 4-voisins mais pas en 8-voisins.

Le benchmark (§6) rejoue ces mêmes invariants sur des centaines
d'instances et **contrôle automatiquement la validité de chaque chemin
produit** (extrémités, obstacles traversés, déplacements légaux).

---

## 2. Structure du projet

```
Projet PA Theme 2/
├── README.md              ce document
├── RESULTATS.md           rapport de mesures (généré par le benchmark)
├── requirements.txt       dépendances (aucune : bibliothèque standard)
├── src/
│   ├── __init__.py
│   ├── grid.py            modèle de grille (cases, voisins, coûts, règle anti-coins)
│   ├── heuristics.py      heuristiques admissibles (Manhattan, Euclidienne, Octile, Chebyshev)
│   ├── result.py          SearchResult : contrat commun des métriques
│   ├── benchmark.py       protocole expérimental + génération de RESULTATS.md
│   ├── selfcheck.py       auto-contrôle du projet (21 vérifications)
│   ├── app.py             interface graphique (tkinter), niveaux 1 à 3
│   └── algorithms/
│       ├── __init__.py    registre des algorithmes
│       ├── base.py        briques communes (budget, reconstruction de chemin)
│       ├── bfs.py         parcours en largeur
│       ├── dfs.py         parcours en profondeur (itératif)
│       ├── dijkstra.py    extension des rayons (référence d'optimalité)
│       ├── astar.py       A* et A* pondéré
│       ├── greedy.py      Greedy Best-First
│       ├── anytime.py     anytime A* (poids décroissants)
│       └── dstar_lite.py  D* Lite (replanification incrémentale)
```

---

## 3. Le modèle de grille

Une grille est un rectangle de `R × C` cases. Chaque case est soit **libre**,
soit **bloquée** (obstacle). Les cases sont stockées à plat : l'indice de la
case `(ligne, colonne)` est `ligne * C + colonne`.

Deux modes de déplacement sont possibles :

| Mode | Voisins | Coût orthogonal | Coût diagonal |
|---|---|---|---|
| **4-voisins** | N, S, E, O | 1 | — (interdit) |
| **8-voisins** | les 4 + les 4 diagonales | 1 | √2 |

**Règle anti-coins** : en 8-voisins, une diagonale est *interdite* si l'une des
deux cases orthogonales adjacentes est bloquée. Sans cette règle, le robot
« couperait » l'angle d'un obstacle ; avec elle, les obstacles sont franchis
de façon réaliste.

**Longueur d'un chemin** = somme des coûts réels des arêtes parcourues
(une diagonale vaut √2). Cette métrique est utilisée dans **toutes** les
comparaisons, y compris pour BFS : BFS minimise le *nombre d'étapes*, son coût
réel peut donc être supérieur à l'optimum en 8-voisins — c'est un résultat
attendu, pas un bogue.

---

## 4. Les algorithmes

### Niveau 1 — panorama

| Algorithme | Principe | Optimal ? |
|---|---|---|
| **BFS** | file FIFO, extension par couches | oui en 4-voisins, **non** en 8-voisins |
| **DFS** | pile LIFO, on s'enfonce au maximum | **jamais** (chemins très longs) |
| **Dijkstra** | plus petit `g(n)` connu | **oui** (coûts positifs) |
| **A\*** | plus petit `f(n) = g(n) + h(n)` | **oui** si `h` est admissible |
| **Greedy** | plus petit `h(n)` seul | **non** (explore peu, chemin parfois long) |

### Niveau 2 — replanification en temps réel

A\* est rejoué dès qu'un obstacle modifie le trajet restant : c'est la
replanification « naïve », qui repart de zéro.

### Niveau 3 — budget et incrémental

* **A\* pondéré** : `f(n) = g(n) + w·h(n)` avec `w ≥ 1`. Le coût obtenu est au
  plus `w` fois l'optimum.
* **Anytime A\*** : on enchaîne des A\* pondérés avec des poids décroissants
  `w = 5 → 3 → 2 → 1,5 → 1`. Une première solution valide arrive très vite,
  chaque itération l'améliore ; si le budget est épuisé, la meilleure solution
  trouvée est renvoyée avec sa **sous-optimalité bornée**. Si l'étape `w = 1`
  se termine, le chemin est **optimal**.
* **D\* Lite** : recherche **à rebours** (de la destination vers le robot) qui
  mémorise ses valeurs de coût d'une recherche à l'autre. Lorsqu'un obstacle
  apparaît ou disparaît, seules les cases impactées (« l'ombre » du
  changement) sont recalculées ; le reste de la carte est réutilisé tel quel.
  Le chemin produit est **optimal** — l'intérêt est le nombre de cases
  re-explorées, pas la qualité du chemin.

### Heuristiques

| Heuristique | Formule | 4-voisins | 8-voisins |
|---|---|---|---|
| Manhattan | `dx + dy` | admissible et exacte | **surestime** (donc interdite) |
| Euclidienne | `√(dx² + dy²)` | admissible (fade) | admissible (fade) |
| Octile | `dx + dy + (√2 − 2)·min(dx, dy)` | admissible | **exacte** (la meilleure) |
| Chebyshev | `max(dx, dy)` | admissible (fade) | exacte si les diagonales coûtent 1 |

L'option « auto » choisit Manhattan en 4-voisins et Octile en 8-voisins.

---

## 5. L'interface graphique

```bash
python -m src.app
```

**Commandes de la souris**

| Geste | Effet |
|---|---|
| clic gauche | poser / retirer un obstacle |
| clic droit | déplacer le départ (le robot) |
| Maj + clic droit | déplacer la destination |

**Raccourcis clavier** : `D` replanification D\* Lite · `A` replanification A\*
depuis zéro · `R` recherche · `Espace` animation.

### Niveau 1 — panorama des algorithmes

Comparaison des cinq algorithmes sur **la même carte** : temps, coût réel,
nombre de cases explorées. Le chemin et la zone explorée sont affichés dans la
grille. Le tableau rappelle que **A\* et Dijkstra doivent trouver le même
coût** : toute divergence signalerait une heuristique non admissible.

### Niveau 2 — carte dynamique

Replanification automatique : dès qu'un obstacle coupe le trajet restant,
A\* est rejoué et le nouveau chemin est affiché. Le robot peut être animé le
long du chemin.

### Niveau 3 — budget et replanification incrémentale

* curseur de **budget** (1 à 1000 ms) pour l'anytime A\* : le tableau montre
  le coût obtenu à chaque itération (poids `w`) et la sous-optimalité bornée ;
* curseur de **poids** pour l'A\* pondéré ;
* boutons **« Replanifier : D\* Lite »** et **« Replanifier : A\* depuis
  zéro »** : les métriques des deux méthodes sont affichées côte à côte, ce
  qui met en évidence l'intérêt de la replanification incrémentale.

---

## 6. Protocole expérimental

Le benchmark (`python -m src.benchmark`) applique le protocole suivant :

* **tailles** : 20×20, 50×50, 100×100 ;
* **densités d'obstacles** : 10 %, 20 %, 30 % ;
* **modes** : 4-voisins et 8-voisins ;
* **30 grilles aléatoires** par combinaison, avec une **graine fixée** ;
* **les mêmes instances** (grilles, départ, arrivée) sont utilisées pour tous
  les algorithmes ;
* une **exécution de chauffe** précède la campagne ;
* le **temps mesuré est celui de la recherche seule** (`time.perf_counter()`),
  affichage exclu ;
* agrégation par **moyenne, médiane et écart-type** ;
* **expérience de replanification** : 100 modifications d'obstacles sur une
  grille 100×100, comparaison « A\* depuis zéro » et « D\* Lite ».

Les résultats mesurés sont dans **`RESULTATS.md`** (généré, jamais écrit à la
main).

---

## 7. Dépendances

**Aucune.** Le projet n'utilise que la bibliothèque standard de Python 3.11+ :
`tkinter` (interface), `heapq` (files de priorité), `statistics` (agrégats),
`random` (génération des cartes), `time` (mesures).

Le fichier `requirements.txt` est donc vide de toute dépendance réelle : il
n'est là que pour documenter le prérequis, et `pip install -r requirements.txt`
reste sans effet.

> L'interface `tkinter` est fournie avec Python sur Windows et macOS. Sur
> certaines distributions Linux, installez le paquet `python3-tk`
> (`sudo apt install python3-tk`).

---

## 8. Vérifier que tout fonctionne

```bash
cd "D:\Projet PA Theme 2"
python -m src.selfcheck      # 21 contrôles de correctness
python -m src.benchmark      # mesures réelles → RESULTATS.md
python -m src.app            # interface graphique
```
