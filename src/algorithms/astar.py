r"""
A\* et A\* pondéré.

A\* — la file de priorité est ordonnée par ``f(n) = g(n) + h(n)`` où ``h``
oriente la recherche vers la destination.

```
open ← file de priorité contenant (start, f = h(start))
g[start] ← 0
tant que open n'est pas vide :
    n ← extraire le sommet de plus petit f
    si n == goal : reconstruire et renvoyer le chemin
    pour chaque voisin m de n (libre, mouvement autorisé) :
        nouveau_g ← g[n] + coût(n, m)
        si nouveau_g < g[m] (ou m jamais vu) :
            g[m] ← nouveau_g ; parent[m] ← n
            insérer (m, f = nouveau_g + h(m)) dans open
renvoyer échec
```

**Propriétés**

* **optimal si ``h`` est admissible** ; si ``h`` est en plus **cohérente**
  (monotone), un sommet n'est développé qu'une seule fois ;
* pire cas identique à Dijkstra, mais **beaucoup moins de cases explorées**
  avec une bonne heuristique ;
* **départage des égalités** : à ``f`` égal, on préfère le plus grand ``g``
  (le sommet le plus proche du but), ce qui réduit encore l'exploration.

A\* pondéré — ``f(n) = g(n) + w·h(n)`` avec ``w ≥ 1``. Le coût du chemin
trouvé est **au plus ``w`` fois le coût optimal** (sous-optimalité bornée) et
beaucoup moins de cases sont explorées quand ``w > 1``. C'est la brique de base
de l'anytime A\* du niveau 3.
"""

from __future__ import annotations

import heapq
import time

from ..grid import Grid
from ..heuristics import HEURISTICS, resolve_heuristic
from ..result import SearchResult
from .base import INF, Budget, build_result, check_start_goal, reconstruct_path

#: Fréquence (en vertex extraits) des vérifications de budget temporel.
_CHECK_EVERY = 256


def astar(
    grid: Grid,
    start: int,
    goal: int,
    mode: str = "4",
    heuristic: str = "auto",
    weight: float = 1.0,
    budget_ms: float | None = None,
    deadline_ms: float | None = None,
    **_: object,
) -> SearchResult:
    r"""Recherche d'un chemin par A\* (ou A\* pondéré si ``weight > 1``).

    Paramètres
    -----------
    weight : float
        Poids appliqué à l'heuristique (``1`` → A\* optimal, ``> 1`` → A\* pondéré).
    budget_ms : float | None
        Budget temps de la recherche. Si la recherche est interrompue, le
        résultat est marqué ``found=False`` avec ``extra["interrompu"]=True``.
    deadline_ms : float | None
        Échéance absolue (en ms depuis l'appel) au-delà de laquelle la
        recherche s'arrête.
    """
    name = "A*" if weight == 1.0 else f"A* pondéré (w={weight:g})"
    invalid = check_start_goal(grid, start, goal)
    if invalid is not None:
        invalid.name = name
        return invalid

    h_name = resolve_heuristic(mode, heuristic)
    h = HEURISTICS[h_name]

    t0 = time.perf_counter()
    neighbors = grid.neighbors_for(mode)
    blocked = grid.blocked
    size = grid.size
    cols = grid.cols
    goal_r, goal_c = divmod(goal, cols)

    g = [INF] * size
    g[start] = 0.0
    parent = [-1] * size

    # Heuristique du départ.
    sr, sc = divmod(start, cols)
    h0 = h(abs(goal_r - sr), abs(goal_c - sc))

    # ``-g`` en second élément : à f égal, on préfère le plus grand g.
    heap: list[tuple[float, float, int]] = [(h0, 0.0, start)]
    explored = 0
    max_open = 1
    found = False
    interrupted = False
    visited: list[int] = []

    budget = Budget(budget_ms)
    deadline = (t0 + deadline_ms / 1000.0) if deadline_ms is not None else None

    while heap:
        _f, neg_g, current = heapq.heappop(heap)
        gcur = -neg_g
        if gcur > g[current]:
            continue  # entrée périmée
        explored += 1
        visited.append(current)
        if current == goal:
            found = True
            break

        if explored % _CHECK_EVERY == 0:
            if budget_ms is not None and budget.elapsed() >= budget_ms:
                interrupted = True
                break
            if deadline is not None and time.perf_counter() > deadline:
                interrupted = True
                break

        cr, cc = divmod(current, cols)
        for nbr, cost, side_a, side_b in neighbors[current]:
            if blocked[nbr]:
                continue
            if side_a >= 0 and (blocked[side_a] or blocked[side_b]):
                continue  # règle anti-coins
            ng = gcur + cost
            if ng < g[nbr]:
                g[nbr] = ng
                parent[nbr] = current
                nr, nc = divmod(nbr, cols)
                nh = h(abs(goal_r - nr), abs(goal_c - nc))
                heapq.heappush(heap, (ng + weight * nh, -ng, nbr))
                if len(heap) > max_open:
                    max_open = len(heap)

    elapsed = (time.perf_counter() - t0) * 1000.0

    if not found:
        return build_result(
            grid,
            name,
            False,
            [],
            0.0,
            explored,
            max_open,
            elapsed,
            interrompu=interrupted,
            heuristique=h_name,
            poids=weight,
            visites=visited,
        )

    path = reconstruct_path(parent, start, goal)
    cost = grid.path_cost(path, mode)
    return build_result(
        grid,
        name,
        True,
        path,
        cost,
        explored,
        max_open,
        elapsed,
        interrompu=interrupted,
        heuristique=h_name,
        poids=weight,
        visites=visited,
    )


def weighted_astar(
    grid: Grid,
    start: int,
    goal: int,
    mode: str = "4",
    heuristic: str = "auto",
    weight: float = 2.0,
    **kwargs: object,
) -> SearchResult:
    r"""A\* pondéré : ``f(n) = g(n) + w·h(n)``."""
    return astar(grid, start, goal, mode, heuristic, weight=weight, **kwargs)
