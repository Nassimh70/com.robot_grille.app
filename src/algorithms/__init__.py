"""
Registre des algorithmes de recherche de chemin.

Chaque algorithme expose la même signature :

``f(grid, start, goal, mode="4", heuristic="auto", **options) -> SearchResult``

où ``start`` et ``goal`` sont des indices à plat (voir :class:`src.grid.Grid`).
"""

from __future__ import annotations

from typing import Callable

from ..result import SearchResult
from .anytime import WEIGHT_SCHEDULE, anytime_astar
from .astar import astar, weighted_astar
from .base import Budget, reconstruct_path
from .bfs import bfs
from .dfs import dfs
from .dijkstra import dijkstra
from .dstar_lite import DStarLite, dstar_lite, dstar_lite_replan
from .greedy import greedy

SearchFunction = Callable[..., SearchResult]

#: Algorithmes évalués par le benchmark, dans l'ordre du document.
ALGORITHMS: dict[str, SearchFunction] = {
    "BFS": bfs,
    "DFS": dfs,
    "Dijkstra": dijkstra,
    "A*": astar,
    "Greedy": greedy,
    "A* pondéré (w=2)": weighted_astar,
    "Anytime A*": anytime_astar,
    "D* Lite": dstar_lite,
}

#: Algorithmes utiles au niveau 1 (panorama complet).
LEVEL1_ALGORITHMS = ("BFS", "DFS", "Dijkstra", "A*", "Greedy")

__all__ = [
    "ALGORITHMS",
    "LEVEL1_ALGORITHMS",
    "WEIGHT_SCHEDULE",
    "Budget",
    "SearchResult",
    "DStarLite",
    "anytime_astar",
    "astar",
    "bfs",
    "dfs",
    "dijkstra",
    "dstar_lite",
    "dstar_lite_replan",
    "greedy",
    "reconstruct_path",
    "weighted_astar",
]
