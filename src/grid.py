"""
Modèle de la grille et calcul des voisins.

La grille est un ensemble de cases ``R × C``. Chaque case libre est un sommet
d'un graphe ; deux cases voisines libres sont reliées par une arête.

Deux modes de déplacement sont gérés :

* **4-voisins** : haut, bas, gauche, droite — coût 1 ;
* **8-voisins** : diagonales ajoutées — coût 1 (orthogonal) ou √2 (diagonale),
  avec la **règle anti-coins** : une diagonale est interdite si l'une des deux
  cases orthogonales adjacentes est un obstacle (le robot ne « traverse »
  pas l'angle d'un mur).

Représentation interne
----------------------
La grille est stockée à plat : la case ``(r, c)`` porte l'indice ``r * cols + c``.
Un ``bytearray`` memorise les obstacles (1 = bloqué, 0 = libre). Les listes de
voisins sont précalculées par mode (géométrie uniquement) ; la filtrage des
obstacles et la règle anti-coins sont appliqués *au moment de l'exploration*,
car la carte change en temps réel (niveau 2 et 3).
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence

SQRT2 = math.sqrt(2.0)

#: Modes de déplacement supportés.
MODES = ("4", "8")

#: Directions (drow, dcol) et coût du déplacement associé.
_OFFSETS: dict[str, tuple[tuple[int, int, float], ...]] = {
    "4": (
        (-1, 0, 1.0),
        (1, 0, 1.0),
        (0, -1, 1.0),
        (0, 1, 1.0),
    ),
    "8": (
        (-1, 0, 1.0),
        (1, 0, 1.0),
        (0, -1, 1.0),
        (0, 1, 1.0),
        (-1, -1, SQRT2),
        (-1, 1, SQRT2),
        (1, -1, SQRT2),
        (1, 1, SQRT2),
    ),
}


class Grid:
    """Grille rectangulaire de cases, certaines étant des obstacles.

    Attributs
    ---------
    rows, cols : int
        Dimensions de la grille.
    blocked : bytearray
        ``1`` si la case est un obstacle, ``0`` sinon (indexation à plat).
    """

    __slots__ = ("rows", "cols", "blocked", "_neighbors")

    def __init__(self, rows: int, cols: int, blocked: Iterable[int] | None = None) -> None:
        if rows <= 0 or cols <= 0:
            raise ValueError("Les dimensions de la grille doivent être positives.")
        self.rows = rows
        self.cols = cols
        if blocked is None:
            self.blocked = bytearray(rows * cols)
        else:
            data = bytearray(blocked)
            if len(data) != rows * cols:
                raise ValueError("Le tampon d'obstacles ne correspond pas aux dimensions.")
            self.blocked = data
        self._neighbors: dict[str, list[tuple[int, float, int, int]]] = {}

    # ------------------------------------------------------------------ taille

    @property
    def size(self) -> int:
        """Nombre total de cases."""
        return self.rows * self.cols

    def __len__(self) -> int:
        return self.rows * self.cols

    def __repr__(self) -> str:  # pragma: no cover - utilitaire de débogage
        return f"Grid({self.rows}x{self.cols}, {sum(self.blocked)} obstacles)"

    # -------------------------------------------------------------- conversions

    def index(self, r: int, c: int) -> int:
        """Indice à plat de la case ``(r, c)``."""
        return r * self.cols + c

    def coords(self, cell: int) -> tuple[int, int]:
        """Couple ``(r, c)`` correspondant à l'indice à plat ``cell``."""
        return divmod(cell, self.cols)

    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.rows and 0 <= c < self.cols

    # ---------------------------------------------------------------- obstacles

    def is_blocked(self, cell: int) -> bool:
        return self.blocked[cell] == 1

    def set_blocked(self, cell: int, value: bool) -> None:
        """Modifie l'état d'obstacle d'une case."""
        self.blocked[cell] = 1 if value else 0

    def toggle(self, cell: int) -> None:
        self.blocked[cell] ^= 1

    def free_cells(self) -> list[int]:
        return [i for i, b in enumerate(self.blocked) if not b]

    def copy(self) -> "Grid":
        """Copie indépendante de la grille (mêmes dimensions, mêmes obstacles)."""
        clone = Grid.__new__(Grid)
        clone.rows = self.rows
        clone.cols = self.cols
        clone.blocked = bytearray(self.blocked)
        clone._neighbors = {}
        return clone

    # ------------------------------------------------------------------ voisins

    def _build_neighbors(self, mode: str) -> list[tuple[int, float, int, int]]:
        """Précalcule la géométrie des voisins pour un mode donné.

        Chaque voisin est décrit par ``(indice, coût, case_latérale_1,
        case_latérale_2)``. Pour un déplacement orthogonal les deux cases
        latérales valent ``-1`` (inutiles) ; pour une diagonale ce sont les deux
        cases orthogonales adjacentes qui doivent être libres (règle anti-coins).
        """
        rows, cols = self.rows, self.cols
        offsets = _OFFSETS[mode]
        table: list[tuple[int, float, int, int]] = []
        for r in range(rows):
            base = r * cols
            for c in range(cols):
                cell = base + c
                nbrs: list[tuple[int, float, int, int]] = []
                for dr, dc, cost in offsets:
                    nr, nc = r + dr, c + dc
                    if nr < 0 or nr >= rows or nc < 0 or nc >= cols:
                        continue
                    if cost == 1.0:
                        nbrs.append((nr * cols + nc, 1.0, -1, -1))
                    else:
                        side_a = (r + dr) * cols + c
                        side_b = r * cols + (c + dc)
                        nbrs.append((nr * cols + nc, SQRT2, side_a, side_b))
                table.append(tuple(nbrs))
        return table

    def neighbors_for(self, mode: str) -> list[tuple[int, float, int, int]]:
        """Table de voisins géométriques pour le mode demandé (mise en cache)."""
        if mode not in _OFFSETS:
            raise ValueError(f"Mode de déplacement inconnu : {mode!r}")
        table = self._neighbors.get(mode)
        if table is None:
            table = self._build_neighbors(mode)
            self._neighbors[mode] = table
        return table

    def move_allowed(self, cell: int, mode: str) -> bool:
        """Vrai si ``cell`` est libre et déplaçable depuis un voisin orthogonal."""
        return not self.blocked[cell]

    def step_cost(self, mode: str) -> float:
        """Coût d'un pas orthogonal (1.0 dans les deux modes)."""
        return 1.0

    def diagonal_cost(self, mode: str) -> float:
        """Coût d'un pas diagonal (√2 en mode 8-voisins, sinon inutilisé)."""
        return SQRT2 if mode == "8" else 1.0

    # ------------------------------------------------------------------ chemins

    def validate_path(
        self,
        path: Sequence[int],
        start: int,
        goal: int,
        mode: str = "4",
    ) -> list[str]:
        """Vérifie qu'un chemin est *légal* et renvoie la liste des anomalies.

        Contrôles effectués :

        * le chemin commence au départ et finit à l'arrivée ;
        * chaque case du chemin est libre (aucun obstacle traversé) ;
        * deux cases consécutives sont bien voisines dans le mode demandé ;
        * en 8-voisins, une diagonale respecte la **règle anti-coins** :
          les deux cases orthogonales adjacentes doivent être libres.

        Une liste vide signifie que le chemin est valide.
        """
        problems: list[str] = []
        if not path:
            return ["chemin vide"]
        if path[0] != start:
            problems.append(f"départ incorrect (attendu {start}, obtenu {path[0]})")
        if path[-1] != goal:
            problems.append(f"arrivée incorrecte (attendue {goal}, obtenue {path[-1]})")

        neighbors = self.neighbors_for(mode)
        for cell in path:
            if not (0 <= cell < self.size):
                problems.append(f"case hors grille : {cell}")
            elif self.blocked[cell]:
                problems.append(f"obstacle traversé : case {cell}")

        for a, b in zip(path, path[1:]):
            if a == b:
                problems.append(f"déplacement nul : case {a}")
                continue
            allowed = {
                nbr: (side_a, side_b)
                for nbr, _cost, side_a, side_b in neighbors[a]
            }
            if b not in allowed:
                problems.append(f"déplacement illegal : {a} -> {b}")
                continue
            side_a, side_b = allowed[b]
            if side_a >= 0 and (self.blocked[side_a] or self.blocked[side_b]):
                problems.append(f"règle anti-coins violée : {a} -> {b}")
        return problems

    def path_cost(self, path: Sequence[int], mode: str) -> float:
        """Coût réel de déplacement d'un chemin (indice à plat).

        En mode 8-voisins les diagonales comptent √2 : c'est cette valeur qui
        sert de métrique « longueur du chemin » dans les comparaisons, même
        pour les algorithmes qui optimisent le *nombre d'étapes* (BFS).

        En mode 4-voisins un pas diagonal n'existe pas ; s'il apparaît malgré
        tout (chemin invalide), il est compté au prix du détour orthogonal
        équivalent, soit 2.
        """
        if len(path) < 2:
            return 0.0
        diagonal = SQRT2 if mode == "8" else 2.0
        total = 0.0
        for a, b in zip(path, path[1:]):
            ar, ac = divmod(a, self.cols)
            br, bc = divmod(b, self.cols)
            if ar != br and ac != bc:
                total += diagonal
            else:
                total += 1.0
        return total

    def path_steps(self, path: Sequence[int]) -> int:
        """Nombre de déplacements effectués par le chemin."""
        return max(0, len(path) - 1)

    def neighbors_free(self, cell: int, mode: str) -> list[tuple[int, float]]:
        """Voisins *effectivement franchissables* d'une case (obstacles pris en compte)."""
        blocked = self.blocked
        out: list[tuple[int, float]] = []
        for nbr, cost, side_a, side_b in self.neighbors_for(mode)[cell]:
            if blocked[nbr]:
                continue
            if side_a >= 0 and (blocked[side_a] or blocked[side_b]):
                continue
            out.append((nbr, cost))
        return out

    def is_reachable(self, start: int, goal: int, mode: str = "4") -> bool:
        """Test de connexité simple (utilisé pour valider les tirages du benchmark)."""
        if self.blocked[start] or self.blocked[goal]:
            return False
        seen = bytearray(self.size)
        seen[start] = 1
        stack = [start]
        while stack:
            cur = stack.pop()
            if cur == goal:
                return True
            for nbr, _cost, side_a, side_b in self.neighbors_for(mode)[cur]:
                if seen[nbr] or self.blocked[nbr]:
                    continue
                if side_a >= 0 and (self.blocked[side_a] or self.blocked[side_b]):
                    continue
                seen[nbr] = 1
                stack.append(nbr)
        return False
