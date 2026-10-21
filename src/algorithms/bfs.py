"""
BFS — parcours en largeur.

On explore les cases par « couches » concentriques autour du départ, à l'aide
d'une file FIFO.

**Propriétés**

* complexité temps et espace : ``O(V + E)`` ;
* chemin avec le **moins d'étapes** ;
* optimal en coût **seulement si tous les coûts sont égaux** : en 4-voisins il
  est donc optimal, mais en 8-voisins (diagonales à √2) il ne l'est plus — le
  coût réel du chemin retourné est plus grand que l'optimum.

En mode 8-voisins, BFS explore « à pas unitaires » (une diagonale vaut un
étaple comme un pas orthogonal) : c'est la seule façon de rester un BFS. La
métrique « longueur du chemin » du benchmark utilise toujours le coût réel
(√2 pour les diagonales), ce qui rend la comparaison honnête.
"""

from __future__ import annotations

import time
from collections import deque

from ..grid import Grid
from ..result import SearchResult
from .base import build_result, check_start_goal, reconstruct_path


def bfs(
    grid: Grid,
    start: int,
    goal: int,
    mode: str = "4",
    heuristic: str = "auto",
    **_: object,
) -> SearchResult:
    """Recherche d'un chemin par parcours en largeur."""
    invalid = check_start_goal(grid, start, goal)
    if invalid is not None:
        invalid.name = "BFS"
        return invalid

    t0 = time.perf_counter()
    neighbors = grid.neighbors_for(mode)
    blocked = grid.blocked
    size = grid.size

    parent = [-1] * size
    seen = bytearray(size)
    seen[start] = 1

    queue = deque([start])
    explored = 0
    max_open = 1
    found = False
    visited: list[int] = []

    while queue:
        current = queue.popleft()
        explored += 1
        visited.append(current)
        if current == goal:
            found = True
            break
        for nbr, _cost, side_a, side_b in neighbors[current]:
            if seen[nbr] or blocked[nbr]:
                continue
            if side_a >= 0 and (blocked[side_a] or blocked[side_b]):
                continue  # règle anti-coins
            seen[nbr] = 1
            parent[nbr] = current
            queue.append(nbr)
            if len(queue) > max_open:
                max_open = len(queue)

    elapsed = (time.perf_counter() - t0) * 1000.0

    if not found:
        return build_result(
            grid, "BFS", False, [], 0.0, explored, max_open, elapsed, visites=visited
        )

    path = reconstruct_path(parent, start, goal)
    cost = grid.path_cost(path, mode)
    return build_result(
        grid, "BFS", True, path, cost, explored, max_open, elapsed, visites=visited
    )
