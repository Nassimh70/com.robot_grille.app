r"""
Briques communes aux algorithmes de recherche de chemin.

Le module expose :

* :func:`reconstruct_path` — reconstruction d'un chemin à partir du tableau
  des parents ;
* :class:`Budget` — minuterie de budget temporel (utilisée par l'anytime A\*) ;
* :func:`check_start_goal` — validation des entrées communes.
"""

from __future__ import annotations

import time
from typing import Sequence

from ..grid import Grid
from ..result import SearchResult

INF = float("inf")


class Budget:
    """Budget temporel écoulé, mesuré en millisecondes.

    ``expired`` passe à ``True`` dès que le délai est dépassé. Les algorithmes
    interrogent ce drapeau régulièrement (tous les ``_CHECK_EVERY`` vertex
    extraits) afin de pouvoir interrompre une recherche en cours.
    """

    __slots__ = ("limit_ms", "_start", "expired", "elapsed_ms")

    #: Nombre de vertices extraits entre deux vérification du budget.
    _CHECK_EVERY = 256

    def __init__(self, limit_ms: float | None = None) -> None:
        self.limit_ms = limit_ms
        self._start = time.perf_counter()
        self.expired = False
        self.elapsed_ms = 0.0

    def start(self) -> None:
        """Remet le chronomètre à zéro (nouvelle itération)."""
        self._start = time.perf_counter()
        self.expired = False
        self.elapsed_ms = 0.0

    def tick(self, counter: int) -> bool:
        """Vérifie périodiquement le dépassement du budget.

        Renvoie ``True`` si le budget est épuisé (et mémorise le temps passé).
        """
        if self.limit_ms is None:
            return False
        if counter % self._CHECK_EVERY == 0:
            self.elapsed_ms = (time.perf_counter() - self._start) * 1000.0
            if self.elapsed_ms >= self.limit_ms:
                self.expired = True
                return True
        return False

    def elapsed(self) -> float:
        """Temps écoulé en millisecondes."""
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000.0
        return self.elapsed_ms


def check_start_goal(grid: Grid, start: int, goal: int) -> SearchResult | None:
    """Vérifie la validité du départ et de l'arrivée.

    Renvoie un résultat d'échec si l'un des deux est un obstacle, sinon ``None``.
    """
    if not (0 <= start < grid.size) or not (0 <= goal < grid.size):
        raise ValueError("Départ ou arrivée hors de la grille.")
    if grid.is_blocked(start) or grid.is_blocked(goal):
        res = SearchResult(found=False, name="")
        res.extra["reason"] = "départ ou arrivée sur un obstacle"
        return res
    return None


def reconstruct_path(parent: Sequence[int], start: int, goal: int) -> list[int]:
    """Reconstruit le chemin ``start → goal`` à partir du tableau des parents."""
    path = [goal]
    node = goal
    guard = 0
    limit = len(parent) + 1
    while node != start:
        node = parent[node]
        path.append(node)
        guard += 1
        if guard > limit:  # pragma: no cover - garde-fou (cycle impossible)
            raise RuntimeError("Cycle détecté lors de la reconstruction du chemin.")
    path.reverse()
    return path


def build_result(
    grid: Grid,
    name: str,
    found: bool,
    path: Sequence[int],
    cost: float,
    explored: int,
    max_open: int,
    elapsed_ms: float,
    **extra,
) -> SearchResult:
    """Assemble un :class:`SearchResult` à partir des mesures brutes."""
    return SearchResult(
        found=found,
        path=list(path),
        cost=cost,
        explored=explored,
        max_open=max_open,
        time_ms=elapsed_ms,
        steps=grid.path_steps(path),
        name=name,
        extra=extra,
    )
