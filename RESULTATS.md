# Résultats expérimentaux

Ce fichier est **généré automatiquement** par `python -m src.benchmark`.

## 1. Protocole

- Tailles : 20×20, 50×50, 100×100
- Densités d'obstacles : 10%, 20%, 30%
- Modes : 4-voisins, 8-voisins
- Répétitions : 30 grilles par combinaison
- Graine de base : `20240501`
- Les **mêmes instances** (grilles, départ, arrivée) sont utilisées pour tous les algorithmes.
- Départ et arrivée : **coins opposés** de la grille (haut-gauche → bas-droit) ; si ces coins sont séparés par les obstacles, un autre couple de cases connectées est choisi. Les instances retenues sont donc toujours **connexes**.
- Le temps mesuré est celui de la **recherche seule** (`time.perf_counter()`), affichage exclu ; une exécution de chauffe précède la campagne.
- **Longueur du chemin** = coût réel du trajet (diagonale = √2 en 8-voisins), quelle que soit la métrique optimisée par l'algorithme.

## 2. Résultats principaux

Moyennes sur toutes les instances. Le détail par taille/densité/mode figure en section 4.

| Algorithme | Temps moyen (ms) | Temps médian (ms) | Écart-type (ms) | Longueur moyenne | Cases explorées (moy.) | Ouverture max (moy.) | Taux de succès |
|---|---|---|---|---|---|---|---|
| BFS | 16.95 | 4.86 | 27.69 | 89.947 | 3147 | 68 | 100.0% |
| DFS | 5.27 | 3.06 | 5.79 | 1533.773 | 2576 | 1586 | 100.0% |
| Dijkstra | 6.96 | 4.39 | 7.62 | 89.896 | 3148 | 69 | 100.0% |
| A* | 2.79 | 0.99 | 4.02 | 89.896 | 669 | 222 | 100.0% |
| Greedy | 0.47 | 0.36 | 0.39 | 100.127 | 118 | 123 | 100.0% |
| A* pondéré (w=2) | 0.56 | 0.38 | 0.59 | 95.770 | 130 | 123 | 100.0% |
| Anytime A* | 5.32 | 3.60 | 5.41 | 89.896 | 638 | 216 | 100.0% |
| D* Lite | 32.66 | 15.52 | 38.71 | 89.896 | 3143 | 68 | 100.0% |

## 3. Replanification après modification d'obstacle

Grille 100×100, 20% d'obstacles, 8-voisins, 100 modifications successives.

| Méthode | Temps moyen (ms) | Temps médian (ms) | Cases explorées (moy.) | Longueur moyenne |
|---|---|---|---|---|
| A\* depuis zéro | 15.92 | 13.83 | 3774 | 163.521 |
| D\* Lite (incrémental) | 0.52 | 0.08 | 56 | 163.521 |

**Accélération moyenne : ×30.79** — écarts de coût entre A\* et D\* Lite : 0 / 100.

## 4. Détail par configuration

### 20×20 · 10% d'obstacles · 4-voisins (30 instances)

| Algorithme | Temps moyen (ms) | Temps médian (ms) | Longueur moyenne | Cases explorées (moy.) | Taux de succès |
|---|---|---|---|---|---|
| BFS | 0.51 | 0.53 | 36.967 | 351 | 100.0% |
| DFS | 0.97 | 0.91 | 205.500 | 326 | 100.0% |
| Dijkstra | 1.05 | 1.04 | 36.967 | 351 | 100.0% |
| A* | 0.35 | 0.31 | 36.967 | 53 | 100.0% |
| Greedy | 0.22 | 0.21 | 40.033 | 42 | 100.0% |
| A* pondéré (w=2) | 0.27 | 0.21 | 39.233 | 45 | 100.0% |
| Anytime A* | 1.94 | 1.72 | 36.967 | 53 | 100.0% |
| D* Lite | 4.37 | 4.68 | 36.967 | 350 | 100.0% |

### 20×20 · 10% d'obstacles · 8-voisins (30 instances)

| Algorithme | Temps moyen (ms) | Temps médian (ms) | Longueur moyenne | Cases explorées (moy.) | Taux de succès |
|---|---|---|---|---|---|
| BFS | 5.99 | 3.75 | 28.395 | 350 | 100.0% |
| DFS | 1.04 | 1.07 | 206.160 | 326 | 100.0% |
| Dijkstra | 0.84 | 0.86 | 28.395 | 351 | 100.0% |
| A* | 0.45 | 0.46 | 28.395 | 98 | 100.0% |
| Greedy | 0.13 | 0.13 | 28.618 | 24 | 100.0% |
| A* pondéré (w=2) | 0.13 | 0.13 | 28.637 | 24 | 100.0% |
| Anytime A* | 1.14 | 1.14 | 28.395 | 46 | 100.0% |
| D* Lite | 4.41 | 3.93 | 28.395 | 350 | 100.0% |

### 20×20 · 20% d'obstacles · 4-voisins (30 instances)

| Algorithme | Temps moyen (ms) | Temps médian (ms) | Longueur moyenne | Cases explorées (moy.) | Taux de succès |
|---|---|---|---|---|---|
| BFS | 0.47 | 0.50 | 32.833 | 288 | 100.0% |
| DFS | 0.48 | 0.46 | 141.833 | 248 | 100.0% |
| Dijkstra | 0.75 | 0.83 | 32.833 | 287 | 100.0% |
| A* | 0.23 | 0.22 | 32.833 | 54 | 100.0% |
| Greedy | 0.12 | 0.13 | 36.900 | 42 | 100.0% |
| A* pondéré (w=2) | 0.14 | 0.14 | 35.033 | 45 | 100.0% |
| Anytime A* | 1.33 | 1.41 | 32.833 | 53 | 100.0% |
| D* Lite | 2.45 | 2.45 | 32.833 | 274 | 100.0% |

### 20×20 · 20% d'obstacles · 8-voisins (30 instances)

| Algorithme | Temps moyen (ms) | Temps médian (ms) | Longueur moyenne | Cases explorées (moy.) | Taux de succès |
|---|---|---|---|---|---|
| BFS | 2.25 | 1.81 | 27.156 | 288 | 100.0% |
| DFS | 0.57 | 0.60 | 142.505 | 248 | 100.0% |
| Dijkstra | 0.74 | 0.78 | 27.112 | 287 | 100.0% |
| A* | 0.50 | 0.49 | 27.112 | 105 | 100.0% |
| Greedy | 0.14 | 0.14 | 28.501 | 28 | 100.0% |
| A* pondéré (w=2) | 0.15 | 0.15 | 27.535 | 30 | 100.0% |
| Anytime A* | 1.88 | 1.73 | 27.112 | 60 | 100.0% |
| D* Lite | 4.35 | 4.69 | 27.112 | 274 | 100.0% |

### 20×20 · 30% d'obstacles · 4-voisins (30 instances)

| Algorithme | Temps moyen (ms) | Temps médian (ms) | Longueur moyenne | Cases explorées (moy.) | Taux de succès |
|---|---|---|---|---|---|
| BFS | 0.21 | 0.26 | 25.533 | 176 | 100.0% |
| DFS | 0.37 | 0.48 | 71.600 | 159 | 100.0% |
| Dijkstra | 0.62 | 0.66 | 25.533 | 177 | 100.0% |
| A* | 0.59 | 0.38 | 25.533 | 49 | 100.0% |
| Greedy | 0.28 | 0.31 | 29.000 | 38 | 100.0% |
| A* pondéré (w=2) | 0.30 | 0.32 | 26.800 | 41 | 100.0% |
| Anytime A* | 1.88 | 2.05 | 25.533 | 46 | 100.0% |
| D* Lite | 2.54 | 2.66 | 25.533 | 170 | 100.0% |

### 20×20 · 30% d'obstacles · 8-voisins (30 instances)

| Algorithme | Temps moyen (ms) | Temps médian (ms) | Longueur moyenne | Cases explorées (moy.) | Taux de succès |
|---|---|---|---|---|---|
| BFS | 2.42 | 2.46 | 22.788 | 175 | 100.0% |
| DFS | 0.59 | 0.71 | 71.780 | 159 | 100.0% |
| Dijkstra | 0.64 | 0.84 | 22.761 | 176 | 100.0% |
| A* | 0.45 | 0.46 | 22.761 | 79 | 100.0% |
| Greedy | 0.17 | 0.15 | 24.252 | 30 | 100.0% |
| A* pondéré (w=2) | 0.17 | 0.17 | 23.200 | 35 | 100.0% |
| Anytime A* | 0.87 | 1.03 | 22.761 | 58 | 100.0% |
| D* Lite | 1.51 | 1.78 | 22.761 | 171 | 100.0% |

### 50×50 · 10% d'obstacles · 4-voisins (30 instances)

| Algorithme | Temps moyen (ms) | Temps médian (ms) | Longueur moyenne | Cases explorées (moy.) | Taux de succès |
|---|---|---|---|---|---|
| BFS | 2.82 | 2.93 | 96.167 | 2244 | 100.0% |
| DFS | 2.89 | 2.64 | 1296.367 | 1963 | 100.0% |
| Dijkstra | 4.75 | 5.09 | 96.167 | 2244 | 100.0% |
| A* | 0.63 | 0.58 | 96.167 | 204 | 100.0% |
| Greedy | 0.32 | 0.32 | 104.900 | 110 | 100.0% |
| A* pondéré (w=2) | 0.35 | 0.34 | 103.100 | 118 | 100.0% |
| Anytime A* | 2.39 | 2.30 | 96.167 | 204 | 100.0% |
| D* Lite | 18.40 | 15.48 | 96.167 | 2221 | 100.0% |

### 50×50 · 10% d'obstacles · 8-voisins (30 instances)

| Algorithme | Temps moyen (ms) | Temps médian (ms) | Longueur moyenne | Cases explorées (moy.) | Taux de succès |
|---|---|---|---|---|---|
| BFS | 15.01 | 12.16 | 72.520 | 2236 | 100.0% |
| DFS | 3.60 | 3.58 | 1303.682 | 1958 | 100.0% |
| Dijkstra | 5.60 | 5.50 | 72.520 | 2241 | 100.0% |
| A* | 1.91 | 1.80 | 72.520 | 396 | 100.0% |
| Greedy | 0.38 | 0.36 | 74.316 | 60 | 100.0% |
| A* pondéré (w=2) | 0.38 | 0.38 | 73.994 | 62 | 100.0% |
| Anytime A* | 4.54 | 4.21 | 72.520 | 319 | 100.0% |
| D* Lite | 24.83 | 22.55 | 72.520 | 2214 | 100.0% |

### 50×50 · 20% d'obstacles · 4-voisins (30 instances)

| Algorithme | Temps moyen (ms) | Temps médian (ms) | Longueur moyenne | Cases explorées (moy.) | Taux de succès |
|---|---|---|---|---|---|
| BFS | 2.26 | 2.32 | 91.667 | 1897 | 100.0% |
| DFS | 3.16 | 3.05 | 927.867 | 1639 | 100.0% |
| Dijkstra | 3.92 | 4.20 | 91.667 | 1897 | 100.0% |
| A* | 0.71 | 0.68 | 91.667 | 228 | 100.0% |
| Greedy | 0.45 | 0.46 | 104.000 | 120 | 100.0% |
| A* pondéré (w=2) | 0.61 | 0.55 | 100.600 | 136 | 100.0% |
| Anytime A* | 4.11 | 4.11 | 91.667 | 221 | 100.0% |
| D* Lite | 20.20 | 22.55 | 91.667 | 1911 | 100.0% |

### 50×50 · 20% d'obstacles · 8-voisins (30 instances)

| Algorithme | Temps moyen (ms) | Temps médian (ms) | Longueur moyenne | Cases explorées (moy.) | Taux de succès |
|---|---|---|---|---|---|
| BFS | 16.95 | 14.94 | 74.207 | 1889 | 100.0% |
| DFS | 6.19 | 5.96 | 931.311 | 1633 | 100.0% |
| Dijkstra | 6.53 | 7.51 | 74.179 | 1892 | 100.0% |
| A* | 2.28 | 2.41 | 74.179 | 632 | 100.0% |
| Greedy | 0.30 | 0.31 | 78.370 | 75 | 100.0% |
| A* pondéré (w=2) | 0.32 | 0.32 | 76.814 | 78 | 100.0% |
| Anytime A* | 3.64 | 3.92 | 74.179 | 555 | 100.0% |
| D* Lite | 16.14 | 16.06 | 74.179 | 1909 | 100.0% |

### 50×50 · 30% d'obstacles · 4-voisins (30 instances)

| Algorithme | Temps moyen (ms) | Temps médian (ms) | Longueur moyenne | Cases explorées (moy.) | Taux de succès |
|---|---|---|---|---|---|
| BFS | 3.30 | 1.86 | 82.367 | 1399 | 100.0% |
| DFS | 2.71 | 2.68 | 466.500 | 1117 | 100.0% |
| Dijkstra | 2.01 | 2.33 | 82.367 | 1399 | 100.0% |
| A* | 0.71 | 0.49 | 82.367 | 278 | 100.0% |
| Greedy | 0.46 | 0.39 | 102.567 | 196 | 100.0% |
| A* pondéré (w=2) | 0.44 | 0.38 | 90.033 | 192 | 100.0% |
| Anytime A* | 2.69 | 2.51 | 82.367 | 270 | 100.0% |
| D* Lite | 8.58 | 9.29 | 82.367 | 1433 | 100.0% |

### 50×50 · 30% d'obstacles · 8-voisins (30 instances)

| Algorithme | Temps moyen (ms) | Temps médian (ms) | Longueur moyenne | Cases explorées (moy.) | Taux de succès |
|---|---|---|---|---|---|
| BFS | 12.95 | 12.18 | 72.847 | 1395 | 100.0% |
| DFS | 2.90 | 3.18 | 467.670 | 1115 | 100.0% |
| Dijkstra | 3.85 | 3.58 | 72.530 | 1398 | 100.0% |
| A* | 2.18 | 2.34 | 72.530 | 658 | 100.0% |
| Greedy | 0.40 | 0.38 | 82.357 | 123 | 100.0% |
| A* pondéré (w=2) | 0.46 | 0.41 | 76.024 | 136 | 100.0% |
| Anytime A* | 5.24 | 4.95 | 72.530 | 575 | 100.0% |
| D* Lite | 13.23 | 13.41 | 72.530 | 1433 | 100.0% |

### 100×100 · 10% d'obstacles · 4-voisins (30 instances)

| Algorithme | Temps moyen (ms) | Temps médian (ms) | Longueur moyenne | Cases explorées (moy.) | Taux de succès |
|---|---|---|---|---|---|
| BFS | 7.16 | 6.84 | 198.000 | 8999 | 100.0% |
| DFS | 9.07 | 9.05 | 5326.800 | 7634 | 100.0% |
| Dijkstra | 12.56 | 12.58 | 198.000 | 8999 | 100.0% |
| A* | 1.83 | 1.67 | 198.000 | 623 | 100.0% |
| Greedy | 0.62 | 0.62 | 215.133 | 222 | 100.0% |
| A* pondéré (w=2) | 0.63 | 0.63 | 212.733 | 228 | 100.0% |
| Anytime A* | 4.78 | 4.61 | 198.000 | 623 | 100.0% |
| D* Lite | 69.77 | 60.80 | 198.000 | 8998 | 100.0% |

### 100×100 · 10% d'obstacles · 8-voisins (30 instances)

| Algorithme | Temps moyen (ms) | Temps médian (ms) | Longueur moyenne | Cases explorées (moy.) | Taux de succès |
|---|---|---|---|---|---|
| BFS | 69.02 | 69.39 | 149.126 | 8999 | 100.0% |
| DFS | 16.19 | 14.69 | 5377.571 | 7625 | 100.0% |
| Dijkstra | 23.81 | 21.51 | 149.126 | 8999 | 100.0% |
| A* | 7.53 | 7.57 | 149.126 | 1795 | 100.0% |
| Greedy | 0.65 | 0.64 | 152.700 | 124 | 100.0% |
| A* pondéré (w=2) | 0.67 | 0.66 | 152.115 | 127 | 100.0% |
| Anytime A* | 11.37 | 10.62 | 149.126 | 1795 | 100.0% |
| D* Lite | 120.45 | 112.52 | 149.126 | 8998 | 100.0% |

### 100×100 · 20% d'obstacles · 4-voisins (30 instances)

| Algorithme | Temps moyen (ms) | Temps médian (ms) | Longueur moyenne | Cases explorées (moy.) | Taux de succès |
|---|---|---|---|---|---|
| BFS | 7.77 | 6.50 | 176.433 | 7275 | 100.0% |
| DFS | 9.62 | 8.85 | 3566.500 | 5877 | 100.0% |
| Dijkstra | 13.46 | 12.28 | 176.433 | 7279 | 100.0% |
| A* | 3.61 | 3.40 | 176.433 | 690 | 100.0% |
| Greedy | 1.16 | 1.22 | 203.633 | 234 | 100.0% |
| A* pondéré (w=2) | 1.33 | 1.34 | 194.567 | 256 | 100.0% |
| Anytime A* | 8.51 | 7.87 | 176.433 | 690 | 100.0% |
| D* Lite | 102.44 | 105.74 | 176.433 | 7327 | 100.0% |

### 100×100 · 20% d'obstacles · 8-voisins (30 instances)

| Algorithme | Temps moyen (ms) | Temps médian (ms) | Longueur moyenne | Cases explorées (moy.) | Taux de succès |
|---|---|---|---|---|---|
| BFS | 99.52 | 100.01 | 143.302 | 7307 | 100.0% |
| DFS | 17.79 | 19.60 | 3590.832 | 5895 | 100.0% |
| Dijkstra | 21.28 | 17.80 | 143.024 | 7292 | 100.0% |
| A* | 10.76 | 11.47 | 143.024 | 2583 | 100.0% |
| Greedy | 0.64 | 0.70 | 152.757 | 148 | 100.0% |
| A* pondéré (w=2) | 0.69 | 0.76 | 149.556 | 157 | 100.0% |
| Anytime A* | 16.11 | 16.15 | 143.024 | 2583 | 100.0% |
| D* Lite | 69.21 | 68.08 | 143.024 | 7346 | 100.0% |

### 100×100 · 30% d'obstacles · 4-voisins (30 instances)

| Algorithme | Temps moyen (ms) | Temps médian (ms) | Longueur moyenne | Cases explorées (moy.) | Taux de succès |
|---|---|---|---|---|---|
| BFS | 5.99 | 6.19 | 153.667 | 5697 | 100.0% |
| DFS | 6.59 | 7.19 | 1754.133 | 4215 | 100.0% |
| Dijkstra | 10.21 | 10.09 | 153.667 | 5702 | 100.0% |
| A* | 6.07 | 4.24 | 153.667 | 1110 | 100.0% |
| Greedy | 1.15 | 1.12 | 190.067 | 282 | 100.0% |
| A* pondéré (w=2) | 1.19 | 1.11 | 170.733 | 335 | 100.0% |
| Anytime A* | 10.83 | 11.81 | 153.667 | 1024 | 100.0% |
| D* Lite | 53.70 | 48.67 | 153.667 | 5598 | 100.0% |

### 100×100 · 30% d'obstacles · 8-voisins (30 instances)

| Algorithme | Temps moyen (ms) | Temps médian (ms) | Longueur moyenne | Cases explorées (moy.) | Taux de succès |
|---|---|---|---|---|---|
| BFS | 50.50 | 45.21 | 135.073 | 5684 | 100.0% |
| DFS | 10.19 | 10.83 | 1759.311 | 4222 | 100.0% |
| Dijkstra | 12.60 | 14.40 | 134.841 | 5698 | 100.0% |
| A* | 9.43 | 9.82 | 134.841 | 2399 | 100.0% |
| Greedy | 0.89 | 0.90 | 154.178 | 218 | 100.0% |
| A* pondéré (w=2) | 1.84 | 1.69 | 143.144 | 295 | 100.0% |
| Anytime A* | 12.45 | 13.75 | 134.841 | 2315 | 100.0% |
| D* Lite | 51.28 | 54.22 | 134.841 | 5599 | 100.0% |

## 5. Contrôle des tendances attendues

Les tendances prévues par le cahier des charges sont **vérifiées automatiquement** sur les mesures ci-dessus.

| Tendance attendue | Constat | Verdict |
|---|---|---|
| A\* et Dijkstra trouvent le **même coût** | écart maximal : 1.42e-14 | ✓ |
| A\* explore **moins** que BFS | 669 contre 3147 cases | ✓ |
| A\* explore **moins** que Dijkstra | 669 contre 3148 cases | ✓ |
| **Greedy** explore le moins de cases | l'algorithme le moins explorant est « Greedy » (118 cases pour Greedy) | ✓ |
| Greedy produit des chemins **plus longs** | 100.13 contre 89.90 pour l'optimum | ✓ |
| **DFS** produit les chemins les **plus longs** | 1534 contre 100 pour « Greedy » | ✓ |
| **D\* Lite** replanifie plus vite qu'**A\* depuis zéro** | ×30.8 en moyenne | ✓ |
| D\* Lite et A\* trouvent le **même chemin** | 0 écart(s) sur 100 modifications | ✓ |

## 6. Lecture des résultats

- Le **nombre de cases explorées** est la mesure la plus fiable : il ne dépend pas de la machine. Le temps, lui, dépend de l'implémentation et du matériel.
- A\* et Dijkstra doivent retrouver **le même coût de chemin** : un écart signalerait une heuristique non admissible ou un bogue.
- BFS est optimal en 4-voisins, mais **pas en 8-voisins** (il minimise le nombre d'étapes, pas le coût réel avec des diagonales à √2).
- Greedy explore très peu mais produit parfois des chemins plus longs ; DFS produit les chemins les plus longs.
- **D\* Lite lancé de zéro est plus lent qu'A\*** : sa recherche va *à rebours*, depuis la destination, et explore donc une zone centrée sur l'arrivée. Son intérêt n'est pas la première recherche mais la **replanification** : après une modification locale, seules les cases impactées sont recalculées (section 3).
- **A\* pondéré** et **anytime A\*** explorent beaucoup moins de cases qu'A\* optimal, au prix d'un chemin plus long — A\* pondéré est borné par le facteur `w`, l'anytime A\* l'est par le poids de sa dernière itération réussie.

---

*Généré par `python -m src.benchmark` — voir `README.md` pour le mode d'emploi.*
