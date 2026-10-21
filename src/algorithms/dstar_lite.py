r"""
D\* Lite — replanification incrémentale (Koenig & Likhachev, 2002).

**Problème.** Aux niveaux 2 et 3, un obstacle apparaît ou disparaît pendant que
le robot avance. Relancer A\* depuis zéro refait tout le calcul alors que la
majeure partie de la carte n'a pas changé.

**Principe.** D\* Lite cherche **à reculons** : de la destination vers le robot.
Il mémorise ses valeurs de coût d'une recherche à l'autre et ne met à jour que
les sommets impactés par un changement.

Fonctionnement de cette implémentation
--------------------------------------
* ``g[u]`` = coût restant de ``u`` jusqu'à la destination ;
* la file de priorité est ordonnée par ``g`` : les sommets sont réglés dans
  l'ordre croissant du coût restant (ordre de Dijkstra), ce qui garantit que
  la valeur retenue est **optimale** ;
* chaque sommet est dans l'un des trois états : *inconnu*, *réglé* (valeur
  fiable) ou *périmé* (valeur à recalculer) ;
* lorsqu'une case change, elle et ses voisins deviennent *périmés* ; le
  recalcul se propage uniquement aux sommets dont la valeur **dépendait**
  de la valeur modifiée (arbre des dépendances) : c'est l'« ombre » du
  changement, seule zone à recalculer ;
* la recherche s'arrête quand plus aucun sommet périmé ne subsiste et qu'aucun
  sommet en attente n'est moins cher que l'estimation du premier pas : le
  premier pas retenu est donc **optimal**, exactement comme celui d'A\*.

La position du robot peut changer sans aucun recalcul : ``g`` ne dépend que de
la carte et de la destination.
"""

from __future__ import annotations

import heapq
import itertools
import time
from typing import Iterable, Iterator

from ..grid import Grid
from ..heuristics import HEURISTICS, resolve_heuristic
from ..result import SearchResult
from .base import INF, build_result, check_start_goal

_EPS = 1e-9

#: États d'un sommet.
UNKNOWN = 0  # jamais calculé
VALID = 1  # valeur fiable
STALE = 2  # valeur à recalculer


class DStarLite:
    """Replanification incrémentale sur une grille.

    Utilisation : on crée l'objet, on appelle :meth:`replan` pour obtenir le
    premier chemin, puis on signale les modifications de la carte avec
    :meth:`set_blocked` (et les déplacements du robot avec :meth:`move_to`)
    avant de rappeler :meth:`replan`.
    """

    def __init__(
        self,
        grid: Grid,
        start: int,
        goal: int,
        mode: str = "4",
        heuristic: str = "auto",
    ) -> None:
        self.grid = grid
        self.mode = mode
        self.start = start
        self.goal = goal
        self.h_name = resolve_heuristic(mode, heuristic)
        self.h = HEURISTICS[self.h_name]

        size = grid.size
        self.g: list[float] = [INF] * size
        self.rhs: list[float] = [INF] * size
        self.state = bytearray(size)
        #: Voisin qui fournit la valeur de chaque sommet (arbre des dépendances).
        self.parent: list[int] = [-1] * size
        #: Relation inverse : enfants d'un sommet.
        self.children: dict[int, set[int]] = {}

        self._heap: list[tuple[float, int, int]] = []
        self._keys: dict[int, float] = {}
        self._counter = itertools.count()
        self._pending = 0

        self.explored = 0
        self.max_open = 0
        self.visited: list[int] = []

        self._neighbors = grid.neighbors_for(mode)
        self._blocked = grid.blocked
        # La destination est la source de la recherche *à rebours* : sa
        # distance restante est nulle.
        self.rhs[self.goal] = 0.0
        self._insert(self.goal)

    # ------------------------------------------------------------- file de priorité

    def _insert(self, node: int) -> None:
        """(Ré)insère un sommet dans la file de priorité."""
        key = self.rhs[node]
        self._keys[node] = key
        heapq.heappush(self._heap, (key, next(self._counter), node))
        if len(self._heap) > self.max_open:
            self.max_open = len(self._heap)

    def _pop(self) -> int | None:
        """Extrait le sommet de plus petite clé valide."""
        while self._heap:
            key, _seq, node = heapq.heappop(self._heap)
            current = self._keys.get(node)
            if current is None:
                continue  # sommet déjà retiré
            if current != key:
                continue  # clé périmée (une version plus récente est en file)
            del self._keys[node]
            return node
        return None

    def _queue_min_key(self) -> float | None:
        """Plus petite clé présente dans la file."""
        while self._heap:
            key, _seq, node = self._heap[0]
            current = self._keys.get(node)
            if current is None or current != key:
                heapq.heappop(self._heap)
                continue
            return key
        return None

    # ------------------------------------------------------------------ moteur

    def _free_neighbors(self, node: int) -> Iterator[tuple[int, float]]:
        """Voisins réellement franchissables d'un sommet."""
        for nbr, cost, side_a, side_b in self._neighbors[node]:
            if self._blocked[nbr]:
                continue
            if side_a >= 0 and (self._blocked[side_a] or self._blocked[side_b]):
                continue  # règle anti-coins
            yield nbr, cost

    def _set_parent(self, node: int, parent: int) -> None:
        """Déclare ``parent`` comme le voisin qui fournit la valeur de ``node``."""
        old_parent = self.parent[node]
        if old_parent == parent:
            return
        if old_parent >= 0:
            siblings = self.children.get(old_parent)
            if siblings is not None:
                siblings.discard(node)
        if parent >= 0:
            self.children.setdefault(parent, set()).add(node)
        self.parent[node] = parent

    def _mark_stale(self, node: int) -> None:
        """Marque un sommet comme périmé (sa valeur doit être recalculée)."""
        if self.state[node] != STALE:
            self.state[node] = STALE
            self._pending += 1
        # La clé provisoire est l'ancienne valeur : elle permet au sommet
        # d'être extrait de la file sans attendre la fin de celle-ci.
        self.rhs[node] = self.g[node]
        if self.rhs[node] == INF:
            self.rhs[node] = 0.0
        self._insert(node)

    def _settle(self, node: int, value: float, parent: int) -> None:
        """Fixe la valeur d'un sommet et propage la mise à jour."""
        previous = self.g[node]
        changed = previous != value and abs(previous - value) > _EPS

        self._set_parent(node, parent)
        self.g[node] = value
        self.rhs[node] = value
        if self.state[node] == STALE:
            self.state[node] = VALID
            self._pending -= 1
        else:
            self.state[node] = VALID

        if changed:
            # Seuls les sommets dont la valeur dépendait de celui-ci sont
            # périmés : c'est ce qui rend la replanification locale.
            for child in list(self.children.get(node, ())):
                self._mark_stale(child)

        for nbr, cost in self._free_neighbors(node):
            if self.state[nbr] != VALID:
                candidate = cost + value
                if candidate < self.rhs[nbr]:
                    self.rhs[nbr] = candidate
                    self._set_parent(nbr, node)
                    self._insert(nbr)

    def _expand(self, node: int) -> None:
        """Développe un sommet : calcule sa valeur à partir des voisins réglés."""
        self.explored += 1
        self.visited.append(node)
        if self.state[node] == VALID:
            return
        if node == self.goal:
            self._settle(node, 0.0, -1)
            return
        value = INF
        parent = -1
        for nbr, cost in self._free_neighbors(node):
            if self.state[nbr] != VALID:
                continue
            candidate = cost + self.g[nbr]
            if candidate < value:
                value = candidate
                parent = nbr
        self._settle(node, value, parent)

    def _lookahead(self) -> float:
        """Estimation du coût du premier pas depuis la position du robot."""
        best = INF
        for nbr, cost in self._free_neighbors(self.start):
            if self.state[nbr] != VALID:
                continue
            candidate = cost + self.g[nbr]
            if candidate < best:
                best = candidate
        return best

    def compute_shortest_path(self) -> None:
        """Recherche à rebours jusqu'à ce que le premier pas soit optimal."""
        safety = 8 * self.grid.size + 2048
        while True:
            key = self._queue_min_key()
            if key is None:
                break
            lookahead = self._lookahead()
            if key >= lookahead - _EPS and self._pending == 0:
                break
            node = self._pop()
            if node is None:
                break
            self._expand(node)
            safety -= 1
            if safety <= 0:  # garde-fou (ne devrait jamais arriver)
                break

    # ------------------------------------------------------------------ publique

    def set_blocked(self, cell: int, blocked: bool) -> None:
        """Signale un changement d'état d'une case (obstacle posé ou retiré)."""
        self.grid.set_blocked(cell, blocked)
        self._mark_stale(cell)
        for nbr, _cost in self._free_neighbors(cell):
            self._mark_stale(nbr)

    def move_to(self, cell: int) -> None:
        """Déplace le robot : aucun recalcul n'est nécessaire."""
        self.start = cell

    def current_path(self) -> list[int] | None:
        """Chemin courant depuis la position du robot (``None`` si inaccessible)."""
        if self._blocked[self.start] or self._blocked[self.goal]:
            return None
        path = [self.start]
        current = self.start
        guard = 0
        limit = self.grid.size + 1
        while current != self.goal:
            guard += 1
            if guard > limit:
                return None
            best = None
            best_value = INF
            for nbr, cost in self._free_neighbors(current):
                if self.state[nbr] != VALID:
                    continue
                candidate = cost + self.g[nbr]
                if candidate < best_value:
                    best_value = candidate
                    best = nbr
            if best is None or best_value == INF:
                return None
            path.append(best)
            current = best
        return path

    def replan(self) -> SearchResult:
        """Recalcule le chemin et renvoie les métriques de la recherche."""
        t0 = time.perf_counter()
        self.explored = 0
        self.visited = []
        self.max_open = len(self._heap)
        self.compute_shortest_path()
        elapsed = (time.perf_counter() - t0) * 1000.0

        path = self.current_path()
        if path is None:
            return build_result(
                self.grid,
                "D* Lite",
                False,
                [],
                0.0,
                self.explored,
                self.max_open,
                elapsed,
                visites=list(self.visited),
            )
        cost = self.grid.path_cost(path, self.mode)
        return build_result(
            self.grid,
            "D* Lite",
            True,
            path,
            cost,
            self.explored,
            self.max_open,
            elapsed,
            visites=list(self.visited),
        )


def dstar_lite(
    grid: Grid,
    start: int,
    goal: int,
    mode: str = "4",
    heuristic: str = "auto",
    **_: object,
) -> SearchResult:
    r"""Recherche D\* Lite « from scratch » (interface commune aux algorithmes)."""
    invalid = check_start_goal(grid, start, goal)
    if invalid is not None:
        invalid.name = "D* Lite"
        return invalid
    planner = DStarLite(grid, start, goal, mode=mode, heuristic=heuristic)
    result = planner.replan()
    result.name = "D* Lite"
    return result


def dstar_lite_replan(
    grid: Grid,
    start: int,
    goal: int,
    changes: Iterable[int],
    mode: str = "4",
    heuristic: str = "auto",
) -> list[SearchResult]:
    """Séquence de replanifications après une série de modifications.

    ``changes`` est la suite des cases modifiées (alternativement obstacle posé
    puis obstacle retiré) ; on renvoie les métriques de chaque replanification.
    """
    planner = DStarLite(grid, start, goal, mode=mode, heuristic=heuristic)
    results = [planner.replan()]
    toggle = True
    for cell in changes:
        planner.set_blocked(cell, toggle)
        toggle = not toggle
        results.append(planner.replan())
    return results
