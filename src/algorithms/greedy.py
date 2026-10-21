"""
Greedy Best-First — priorité sur l'heuristique seule.

La file de priorité est ordonnée par ``h(n)`` uniquement, en ignorant ``g(n)``.

**Propriétés**

* explores **très peu** de cases quand le terrain est dégagé ;
* **aucune garantie d'optimalité** : il peut contourner un obstacle par un
  grand détour.

Rôle dans le projet : illustrer le compromis vitesse/qualité — explorer peu ne
veut pas dire trouver le plus court chemin.
"""

from __future__ import annotations

import heapq
import time

from ..grid import Grid
from ..heuristics import HEURISTICS, resolve_heuristic
from ..result import SearchResult
from .base import INF, build_result, check_start_goal, reconstruct_path


def greedy(
    grid: Grid,
    start: int,
    goal: int,
    mode: str = "4",
    heuristic: str = "auto",
    **_: object,
) -> SearchResult:
    """Recherche gloutonne sur l'heuristique."""
    invalid = check_start_goal(grid, start, goal)
    if invalid is not None:
        invalid.name = "Greedy"
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

    sr, sc = divmod(start, cols)
    heap: list[tuple[float, float, int]] = [
        (h(abs(goal_r - sr), abs(goal_c - sc)), 0.0, start)
    ]
    explored = 0
    max_open = 1
    found = False
    visited: list[int] = []

    while heap:
        _hcur, neg_g, current = heapq.heappop(heap)
        gcur = -neg_g
        if gcur > g[current]:
            continue  # entrée périmée
        explored += 1
        visited.append(current)
        if current == goal:
            found = True
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
                heapq.heappush(heap, (h(abs(goal_r - nr), abs(goal_c - nc)), -ng, nbr))
                if len(heap) > max_open:
                    max_open = len(heap)

    elapsed = (time.perf_counter() - t0) * 1000.0

    if not found:
        return build_result(
            grid, "Greedy", False, [], 0.0, explored, max_open, elapsed, visites=visited
        )

    path = reconstruct_path(parent, start, goal)
    cost = grid.path_cost(path, mode)
    return build_result(
        grid, "Greedy", True, path, cost, explored, max_open, elapsed, visites=visited
    )
