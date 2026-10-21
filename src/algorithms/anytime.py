r"""
Anytime A\* — recherche de chemin sous contrainte de temps (niveau 3).

**Problème.** Le niveau 3 demande le plus court chemin « dans un temps de
calcul borné ». Or A\* optimal peut dépasser le budget sur une grande grille.

**Solution retenue.** On enchaîne des recherches A\* pondérées avec un poids
décroissant, par exemple ``w = 5 → 3 → 2 → 1,5 → 1``.

```
meilleur ← aucun
pour w dans [5, 3, 2, 1.5, 1] :
    chemin ← A*_pondéré(w, avec vérification du budget à chaque itération)
    si budget épuisé : sortir de la boucle
    meilleur ← chemin
renvoyer meilleur (optimal si la dernière étape w = 1 est terminée)
```

* une première solution **valide** arrive très vite (poids élevé) ;
* chaque itération l'améliore, avec une garantie de qualité de plus en plus
  serrée ;
* si le budget est épuisé, on renvoie la meilleure solution déjà trouvée et on
  indique son **facteur de sous-optimalité borné** (au plus ``w``) ;
* si le temps suffit, l'étape ``w = 1`` donne le **chemin optimal**.

Ce mécanisme s'inspire de ARA\* (Anytime Repairing A\*, Likhachev et al., 2003).
"""

from __future__ import annotations

import time

from ..grid import Grid
from ..result import SearchResult
from .astar import astar
from .base import build_result

#: weights décroissants utilisés par défaut.
WEIGHT_SCHEDULE: tuple[float, ...] = (5.0, 3.0, 2.0, 1.5, 1.0)


def anytime_astar(
    grid: Grid,
    start: int,
    goal: int,
    mode: str = "4",
    heuristic: str = "auto",
    budget_ms: float = 50.0,
    weights: tuple[float, ...] = WEIGHT_SCHEDULE,
    **kwargs: object,
) -> SearchResult:
    """Recherche « anytime » : meilleure solution trouvée dans le budget."""
    t0 = time.perf_counter()
    iterations: list[dict[str, float]] = []
    best: SearchResult | None = None
    best_weight = float("inf")
    optimal = False

    for weight in weights:
        elapsed = (time.perf_counter() - t0) * 1000.0
        remaining = budget_ms - elapsed
        if remaining <= 0:
            break

        result = astar(
            grid,
            start,
            goal,
            mode=mode,
            heuristic=heuristic,
            weight=weight,
            budget_ms=remaining,
            **kwargs,
        )
        iterations.append(
            {
                "poids": weight,
                "trouve": 1.0 if result.found else 0.0,
                "cout": result.cost,
                "temps_ms": result.time_ms,
                "explores": float(result.explored),
            }
        )

        if result.found and (best is None or result.cost < best.cost - 1e-9):
            best = result
            best_weight = weight
        if result.found and weight == 1.0:
            optimal = True
        if result.extra.get("interrompu"):
            break

    total_ms = (time.perf_counter() - t0) * 1000.0

    if best is None:
        return build_result(
            grid,
            "Anytime A*",
            False,
            [],
            0.0,
            0,
            0,
            total_ms,
            iterations=iterations,
            budget_ms=budget_ms,
            sous_optimite=float("inf"),
            optimal=False,
        )

    return build_result(
        grid,
        "Anytime A*",
        True,
        best.path,
        best.cost,
        best.explored,
        best.max_open,
        total_ms,
        iterations=iterations,
        budget_ms=budget_ms,
        sous_optimite=best_weight,
        optimal=optimal,
        explorations_cumulées=sum(i["explores"] for i in iterations),
        visites=list(best.extra.get("visites", ())),
    )
