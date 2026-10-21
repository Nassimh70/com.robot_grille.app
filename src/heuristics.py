r"""
Heuristiques admissibles pour A*.

Toutes les heuristiques reçoivent les écarts ``dx`` (lignes) et ``dy``
(columns) entre la case courante et la destination, et renvoient une
**estimation du coût restant**.

Admissibilité
-------------
Une heuristique est *admissible* si elle ne surestime jamais le coût réel du
chemin restant. C'est la condition d'optimalité d'A\*.

* **Manhattan** ``dx + dy`` — 4-voisins (surestime en 8-voisins : à proscrire).
* **Euclidienne** ``√(dx² + dy²)`` — 8-voisins, admissible mais moins informée
  que l'octile.
* **Octile** ``(dx + dy) + (√2 − 2)·min(dx, dy)`` — 8-voisins avec diagonale
  coûtant √2 : la plus précise des quatre.
* **Chebyshev** ``max(dx, dy)`` — 8-voisins avec diagonale de coût 1.
"""

from __future__ import annotations

import math

from .grid import SQRT2

#: Coefficient de l'octile : (dx + dy) + (√2 − 2)·min(dx, dy).
OCTILE_COEF = SQRT2 - 2.0


def manhattan(dx: int, dy: int) -> float:
    """Distance de Manhattan — 4-voisins."""
    return float(dx + dy)


def euclidean(dx: int, dy: int) -> float:
    """Distance euclidienne — 8-voisins (admissible mais peu informée)."""
    return math.sqrt(float(dx * dx + dy * dy))


def octile(dx: int, dy: int) -> float:
    """Distance octile — 8-voisins avec diagonale à √2 (la plus précise)."""
    return float(dx + dy + OCTILE_COEF * (dx if dx < dy else dy))


def chebyshev(dx: int, dy: int) -> float:
    """Distance de Chebyshev — 8-voisins avec diagonale de coût 1."""
    return float(dx if dx > dy else dy)


#: Registre des heuristiques disponibles (clé → fonction).
HEURISTICS = {
    "manhattan": manhattan,
    "euclidean": euclidean,
    "octile": octile,
    "chebyshev": chebyshev,
}

#: Libellés lisibles pour l'interface graphique.
HEURISTIC_LABELS = {
    "manhattan": "Manhattan",
    "euclidean": "Euclidienne",
    "octile": "Octile",
    "chebyshev": "Chebyshev",
}

#: Heuristique recommandée par mode de déplacement.
DEFAULT_HEURISTIC = {
    "4": "manhattan",
    "8": "octile",
}


def resolve_heuristic(mode: str, name: str = "auto") -> str:
    """Renvoie le nom de l'heuristique à utiliser.

    ``"auto"`` (ou ``None``) choisit l'heuristique admissible recommandée pour
    le mode : Manhattan en 4-voisins, Octile en 8-voisins.
    """
    if not name or name == "auto":
        return DEFAULT_HEURISTIC.get(mode, "manhattan")
    if name not in HEURISTICS:
        raise ValueError(f"Heuristique inconnue : {name!r}")
    return name


def is_admissible_for(name: str, mode: str) -> bool:
    r"""Indique si l'heuristique est admissible dans le mode indiqué.

    Manhattan **surestime** en 8-voisins (une diagonale coûte √2 alors que
    Manhattan compte 2 pas orthogonaux) : A\* perdrait alors son optimalité.
    """
    if name == "manhattan":
        return mode == "4"
    if name == "chebyshev":
        return mode == "8"
    return True
