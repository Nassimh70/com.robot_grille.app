"""
DFS — parcours en profondeur.

On s'enfonce le plus loin possible dans une direction avant de revenir en
arrière, à l'aide d'une pile LIFO.

**Propriétés**

* complexité : ``O(V + E)`` ;
* trouve un chemin, **pas le plus court** : les chemins obtenus sont souvent
  longs et tortueux.

L'implémentation est **itérative** (pile explicite) afin d'éviter toute limite
de récursion sur les grandes grilles.
"""

from __future__ import annotations

import time

from ..grid import Grid
from ..result import SearchResult
from .base import build_result, check_start_goal, reconstruct_path


def dfs(
    grid: Grid,
    start: int,
    goal: int,
    mode: str = "4",
    heuristic: str = "auto",
    **_: object,
) -> SearchResult:
    """Recherche d'un chemin par parcours en profondeur."""
    invalid = check_start_goal(grid, start, goal)
    if invalid is not None:
        invalid.name = "DFS"
        return invalid

    t0 = time.perf_counter()
    neighbors = grid.neighbors_for(mode)
    blocked = grid.blocked
    size = grid.size

    parent = [-1] * size
    seen = bytearray(size)
    seen[start] = 1

    # Pile d'exploration : (cellule, index du prochain voisin à examiner).
    stack = [(start, 0)]
    explored = 0
    max_open = 1
    found = False
    visited: list[int] = []

    while stack:
        current, index = stack[-1]
        if index == 0:
            explored += 1
            visited.append(current)
            if current == goal:
                found = True
                break
        nbrs = neighbors[current]
        if index >= len(nbrs):
            stack.pop()
            continue
        stack[-1] = (current, index + 1)
        nbr, _cost, side_a, side_b = nbrs[index]
        if seen[nbr] or blocked[nbr]:
            continue
        if side_a >= 0 and (blocked[side_a] or blocked[side_b]):
            continue  # règle anti-coins
        seen[nbr] = 1
        parent[nbr] = current
        stack.append((nbr, 0))
        if len(stack) > max_open:
            max_open = len(stack)

    elapsed = (time.perf_counter() - t0) * 1000.0

    if not found:
        return build_result(
            grid, "DFS", False, [], 0.0, explored, max_open, elapsed, visites=visited
        )

    path = reconstruct_path(parent, start, goal)
    cost = grid.path_cost(path, mode)
    return build_result(
        grid, "DFS", True, path, cost, explored, max_open, elapsed, visites=visited
    )
