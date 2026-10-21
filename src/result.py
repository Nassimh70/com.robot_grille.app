"""
Structure commune de retour des algorithmes de recherche.

Tous les algorithmes renvoient un :class:`SearchResult` : le jeu de métriques
utilisé dans le benchmark et dans l'interface graphique.

Métriques
---------
``time_ms``      durée de la **recherche seule** (``time.perf_counter()``),
                 affichage exclu ;
``cost``         longueur du chemin trouvé (coût réel des arêtes) ;
``explored``     nombre de sommets extraits de la liste ouverte et développés ;
``max_open``     taille maximale de la liste ouverte (empreinte mémoire) ;
``steps``        nombre de déplacements du chemin.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchResult:
    """Résultat d'une recherche de chemin."""

    found: bool = False
    path: list[int] = field(default_factory=list)
    cost: float = 0.0
    explored: int = 0
    max_open: int = 0
    time_ms: float = 0.0
    steps: int = 0
    name: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def path_coords(self, cols: int) -> list[tuple[int, int]]:
        """Chemin converti en coordonnées ``(ligne, colonne)``."""
        return [divmod(cell, cols) for cell in self.path]

    def summary(self) -> str:
        """Résumé lisible en une ligne (pour l'interface graphique)."""
        if not self.found:
            return f"{self.name}: aucun chemin (temps {self.time_ms:.2f} ms)"
        return (
            f"{self.name}: {self.steps} pas, coût {self.cost:.2f}, "
            f"{self.explored} cases explorées, {self.time_ms:.2f} ms"
        )

    def __repr__(self) -> str:  # pragma: no cover - utilitaire de débogage
        return (
            f"SearchResult(name={self.name!r}, found={self.found}, cost={self.cost:.3f}, "
            f"explored={self.explored}, time_ms={self.time_ms:.3f})"
        )
