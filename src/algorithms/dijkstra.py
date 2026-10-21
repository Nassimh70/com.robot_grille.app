r"""
Dijkstra — plus court chemin par extension des rayons.

On développe toujours le sommet de plus petit ``g(n)`` (coût connu depuis le
départ), à l'aide d'une file de priorité (tas binaire).

**Propriétés**

* complexité : ``O((V + E)·log V)`` ;
* **optimal** pour tout coût positif — donc correct avec les diagonales à √2 ;
* n'utilise aucune information sur la destination : il explore « en cercle »
  dans toutes les directions.

C'est la **référence d'optimalité** du projet : on vérifie que A\* retrouve
exactement le même coût.
"""

from __future__ import annotations

import heapq
import time

from ..grid import Grid
from ..result import SearchResult
from .base import INF, build_result, check_start_goal, reconstruct_path


def dijkstra(
    grid: Grid,
    start: int,
    goal: int,
    mode: str = "4",
    heuristic: str = "auto",
    **_: object,
) -> SearchResult:
    """Recherche d'un plus court chemin par Dijkstra."""
    invalid = check_start_goal(grid, start, goal)
    if invalid is not None:
        invalid.name = "Dijkstra"
        return invalid

    t0 = time.perf_counter()
    neighbors = grid.neighbors_for(mode)
    blocked = grid.blocked
    size = grid.size

    dist = [INF] * size
    dist[start] = 0.0
    parent = [-1] * size

    heap: list[tuple[float, int]] = [(0.0, start)]
    explored = 0
    max_open = 1
    found = False
    visited: list[int] = []

    while heap:
        d, current = heapq.heappop(heap)
        if d > dist[current]:
            continue  # entrée périmée
        explored += 1
        visited.append(current)
        if current == goal:
            found = True
            break
        for nbr, cost, side_a, side_b in neighbors[current]:
            if blocked[nbr]:
                continue
            if side_a >= 0 and (blocked[side_a] or blocked[side_b]):
                continue  # règle anti-coins
            nd = d + cost
            if nd < dist[nbr]:
                dist[nbr] = nd
                parent[nbr] = current
                heapq.heappush(heap, (nd, nbr))
                if len(heap) > max_open:
                    max_open = len(heap)

    elapsed = (time.perf_counter() - t0) * 1000.0

    if not found:
        return build_result(
            grid, "Dijkstra", False, [], 0.0, explored, max_open, elapsed, visites=visited
        )

    path = reconstruct_path(parent, start, goal)
    cost = grid.path_cost(path, mode)
    return build_result(
        grid, "Dijkstra", True, path, cost, explored, max_open, elapsed, visites=visited
    )
