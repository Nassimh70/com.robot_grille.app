r"""
Auto-contrôle du projet — `python -m src.selfcheck`

Ce module remplace une suite de tests externe : il ne dépend que de la
bibliothèque standard et se lance d'une simple commande. Il rejoue les
**invariants de correctness** du projet et affiche un rapport lisible :

```
python -m src.selfcheck
```

* chaque contrôle est une fonction ``check_*`` sans argument, qui lève une
  ``AssertionError`` en cas d'échec ;
* le code de sortie vaut ``0`` si tous les contrôles passent, ``1`` sinon ;
* les mesures du benchmark (``python -m src.benchmark``) complètent ces
  contrôles en rejouant les mêmes invariants sur des centaines d'instances.
"""

from __future__ import annotations

import math
import random
import sys
import traceback
from typing import Callable

from .algorithms import ALGORITHMS
from .algorithms.anytime import anytime_astar
from .algorithms.astar import astar, weighted_astar
from .algorithms.base import reconstruct_path
from .algorithms.bfs import bfs
from .algorithms.dfs import dfs
from .algorithms.dijkstra import dijkstra
from .algorithms.dstar_lite import DStarLite
from .algorithms.greedy import greedy
from .grid import SQRT2, Grid
from .heuristics import chebyshev, euclidean, manhattan, octile

EPS = 1e-9


# ------------------------------------------------------------------ outils


def random_grid(
    rows: int = 20, cols: int = 20, density: float = 0.2, seed: int = 0
) -> Grid:
    """Grille aléatoire (les deux coins opposés sont laissés libres)."""
    rng = random.Random(seed)
    grid = Grid(rows, cols)
    for cell in range(grid.size):
        if rng.random() < density:
            grid.blocked[cell] = 1
    grid.blocked[0] = 0
    grid.blocked[grid.size - 1] = 0
    return grid


def assert_path_valid(grid: Grid, path: list[int], start: int, goal: int, mode: str) -> None:
    """Le chemin doit être continu, libre et respecter la règle anti-coins."""
    assert path, "le chemin ne doit pas être vide"
    assert path[0] == start, "le chemin ne part pas du départ"
    assert path[-1] == goal, "le chemin n'arrive pas à l'arrivée"
    problems = grid.validate_path(path, start, goal, mode)
    assert not problems, "; ".join(problems)


# ------------------------------------------------------------------ contrôles


def check_all_algorithms_find_a_path() -> None:
    """Tous les algorithmes trouvent un chemin valide."""
    for mode in ("4", "8"):
        grid = random_grid(15, 15, 0.15, seed=3)
        for name, func in ALGORITHMS.items():
            result = func(grid, 0, grid.size - 1, mode=mode)
            assert result.found, f"{name} n'a pas trouvé de chemin"
            assert_path_valid(grid, result.path, 0, grid.size - 1, mode)
            assert abs(result.cost - grid.path_cost(result.path, mode)) < EPS
            assert result.explored > 0
            assert result.time_ms >= 0.0


def check_no_path_when_goal_is_blocked() -> None:
    """Aucun chemin n'est annoncé si l'arrivée est bloquée."""
    grid = random_grid(10, 10, 0.1, seed=5)
    grid.blocked[grid.size - 1] = 1
    for name, func in ALGORITHMS.items():
        result = func(grid, 0, grid.size - 1, mode="4")
        assert not result.found, f"{name} aurait dû échouer"


def check_no_path_when_disconnected() -> None:
    """Aucun chemin n'est annoncé si la carte est coupée en deux."""
    grid = Grid(5, 1)
    grid.blocked[2] = 1
    assert not astar(grid, 0, 4, mode="4").found


def check_astar_matches_dijkstra() -> None:
    """A* (heuristique admissible) retrouve exactement le coût de Dijkstra."""
    for mode in ("4", "8"):
        for seed in range(25):
            grid = random_grid(18, 18, 0.2, seed=seed)
            if not grid.is_reachable(0, grid.size - 1, mode):
                continue
            ref = dijkstra(grid, 0, grid.size - 1, mode=mode)
            got = astar(grid, 0, grid.size - 1, mode=mode)
            assert got.found and ref.found
            assert abs(got.cost - ref.cost) < EPS, f"écart de coût (seed {seed}, {mode})"


def check_bfs_optimality() -> None:
    """BFS est optimal en 4-voisins, mais pas en 8-voisins."""
    for mode in ("4", "8"):
        grid = random_grid(12, 12, 0.10, seed=11)
        if not grid.is_reachable(0, grid.size - 1, mode):
            continue
        b = bfs(grid, 0, grid.size - 1, mode=mode)
        d = dijkstra(grid, 0, grid.size - 1, mode=mode)
        if mode == "4":
            assert abs(b.cost - d.cost) < EPS
        else:
            # BFS minimise le nombre d'étapes : son coût réel est au moins celui de Dijkstra.
            assert b.cost >= d.cost - EPS


def check_dfs_path_is_longer() -> None:
    """DFS produit des chemins plus longs que BFS."""
    longer = 0
    trials = 0
    for seed in range(20):
        grid = random_grid(16, 16, 0.15, seed=seed)
        if not grid.is_reachable(0, grid.size - 1, "4"):
            continue
        trials += 1
        b = bfs(grid, 0, grid.size - 1, mode="4")
        d = dfs(grid, 0, grid.size - 1, mode="4")
        if d.cost > b.cost:
            longer += 1
    assert trials > 0
    assert longer > trials / 2, "DFS devrait produire des chemins plus longs"


def check_astar_explores_less_than_dijkstra() -> None:
    """A* explore moins de cases que Dijkstra : c'est tout l'intérêt de l'heuristique."""
    grid = random_grid(40, 40, 0.05, seed=42)
    a = astar(grid, 0, grid.size - 1, mode="4")
    d = dijkstra(grid, 0, grid.size - 1, mode="4")
    assert a.explored < d.explored


def check_greedy_is_fast_but_not_optimal() -> None:
    """Greedy explore peu de cases, mais son chemin n'est pas optimal."""
    grid = random_grid(40, 40, 0.05, seed=13)
    g = greedy(grid, 0, grid.size - 1, mode="8")
    d = dijkstra(grid, 0, grid.size - 1, mode="8")
    assert g.explored <= d.explored
    assert g.cost >= d.cost - EPS


def check_weighted_astar_is_bounded() -> None:
    """Le coût de l'A* pondéré est au plus ``w`` fois l'optimum."""
    for weight in (1.5, 2.0, 3.0):
        grid = random_grid(25, 25, 0.2, seed=17)
        if not grid.is_reachable(0, grid.size - 1, "4"):
            continue
        opt = dijkstra(grid, 0, grid.size - 1, mode="4")
        res = weighted_astar(grid, 0, grid.size - 1, mode="4", weight=weight)
        assert res.cost <= weight * opt.cost + EPS


def check_anytime_astar_converges() -> None:
    """Avec un budget large, l'anytime A* atteint l'optimum."""
    grid = random_grid(20, 20, 0.2, seed=23)
    opt = dijkstra(grid, 0, grid.size - 1, mode="4")
    res = anytime_astar(grid, 0, grid.size - 1, mode="4", budget_ms=5000.0)
    assert res.found
    assert abs(res.cost - opt.cost) < EPS
    assert res.extra["optimal"] is True


def check_anytime_astar_respects_budget() -> None:
    """Avec un budget minuscule, l'anytime A* reste dans le budget."""
    grid = random_grid(60, 60, 0.2, seed=29)
    res = anytime_astar(grid, 0, grid.size - 1, mode="8", budget_ms=1.0)
    assert res.found
    assert res.extra["sous_optimite"] >= 1.0


def check_anytime_astar_improves_with_budget() -> None:
    """Un budget plus large donne un chemin au moins aussi bon."""
    grid = random_grid(45, 45, 0.2, seed=31)
    small = anytime_astar(grid, 0, grid.size - 1, mode="8", budget_ms=0.5)
    large = anytime_astar(grid, 0, grid.size - 1, mode="8", budget_ms=3000.0)
    assert large.cost <= small.cost + EPS


def check_dstar_lite_matches_astar() -> None:
    """D* Lite retrouve exactement le même chemin qu'A* après chaque changement."""
    rng = random.Random(101)
    for mode in ("4", "8"):
        for trial in range(8):
            grid = random_grid(22, 22, 0.18, seed=200 + trial)
            if not grid.is_reachable(0, grid.size - 1, mode):
                continue
            planner = DStarLite(grid, 0, grid.size - 1, mode=mode)
            result = planner.replan()
            assert result.found
            reference = astar(grid, 0, grid.size - 1, mode=mode)
            assert abs(result.cost - reference.cost) < EPS, f"essai {trial} (initial)"

            candidates = [c for c in grid.free_cells() if c not in (0, grid.size - 1)]
            rng.shuffle(candidates)
            for index in range(20):
                cell = candidates[(index + trial) % len(candidates)]
                blocked = bool(index % 2)
                planner.set_blocked(cell, blocked)
                result = planner.replan()
                reference = astar(grid, 0, grid.size - 1, mode=mode)
                if reference.found:
                    assert result.found, f"essai {trial} : D* Lite a échoué"
                    assert abs(result.cost - reference.cost) < EPS, (
                        f"essai {trial}, changement {index} : "
                        f"D* Lite {result.cost} != A* {reference.cost}"
                    )
                    assert_path_valid(grid, result.path, 0, grid.size - 1, mode)
                else:
                    assert not result.found


def check_dstar_lite_follows_robot() -> None:
    """Quand le robot avance, D* Lite conserve un chemin optimal."""
    grid = random_grid(20, 20, 0.15, seed=77)
    planner = DStarLite(grid, 0, grid.size - 1, mode="4")
    result = planner.replan()
    assert result.found
    path = result.path
    for step in range(len(path) - 1):
        planner.move_to(path[step])
        moved = planner.replan()
        assert moved.found
        assert moved.path[0] == path[step]
        reference = astar(grid, path[step], grid.size - 1, mode="4")
        assert abs(moved.cost - reference.cost) < EPS


def check_dstar_lite_is_faster_to_replan() -> None:
    """La replanification incrémentale est plus rapide qu'A* depuis zéro."""
    rng = random.Random(7)
    grid = random_grid(70, 70, 0.15, seed=99)
    planner = DStarLite(grid, 0, grid.size - 1, mode="8")
    planner.replan()

    astar_total = 0.0
    dstar_total = 0.0
    candidates = [c for c in grid.free_cells() if c not in (0, grid.size - 1)]
    rng.shuffle(candidates)
    for index in range(20):
        cell = candidates[index]
        blocked = bool(index % 2)
        grid.set_blocked(cell, blocked)
        astar_total += astar(grid, 0, grid.size - 1, mode="8").time_ms
        planner.set_blocked(cell, blocked)
        dstar_total += planner.replan().time_ms
    assert dstar_total < astar_total, (
        f"D* Lite ({dstar_total:.2f} ms) devrait être plus rapide "
        f"qu'A* ({astar_total:.2f} ms)"
    )


def check_heuristics_admissibility() -> None:
    """Octile est exacte ; Euclidienne et Chebyshev admissibles ; Manhattan surestime en 8-voisins."""
    rng = random.Random(3)
    for _ in range(200):
        dx = rng.randint(0, 12)
        dy = rng.randint(0, 12)
        exact = max(dx, dy) + (SQRT2 - 1.0) * min(dx, dy)
        assert abs(octile(dx, dy) - exact) < EPS
        assert euclidean(dx, dy) <= exact + EPS
        assert chebyshev(dx, dy) <= exact + EPS
        assert manhattan(dx, dy) >= exact - EPS
        # En 4-voisins, Manhattan est exacte.
        assert abs(manhattan(dx, dy) - (dx + dy)) < EPS


def check_anti_corner_rule() -> None:
    """Une diagonale est interdite si une case orthogonale adjacente est bloquée."""
    grid = Grid(3, 3)
    grid.blocked[1] = 1  # case (0,1)
    result = astar(grid, 0, 2, mode="8")
    assert result.found, "le robot doit pouvoir contourner l'obstacle"
    visited = [divmod(cell, 3) for cell in result.path]
    assert (0, 1) not in visited, "le chemin ne doit pas traverser l'obstacle"


def check_manhattan_is_not_optimal_in_eight() -> None:
    """Manhattan en 8-voisins surestime : A* perd alors l'optimalité."""
    grid = random_grid(12, 12, 0.05, seed=77)
    good = astar(grid, 0, grid.size - 1, mode="8", heuristic="octile")
    bad = astar(grid, 0, grid.size - 1, mode="8", heuristic="manhattan")
    assert bad.cost >= good.cost - EPS


def check_path_cost_and_reconstruction() -> None:
    """Le coût réel et la reconstruction de chemin sont cohérents."""
    grid = Grid(2, 2)
    assert abs(grid.path_cost([0, 3], "8") - SQRT2) < EPS
    assert abs(grid.path_cost([0, 3], "4") - 2.0) < EPS  # détour orthogonal
    parent = [-1] * grid.size
    parent[1] = 0
    parent[3] = 1
    assert reconstruct_path(parent, 0, 3) == [0, 1, 3]


def check_grid_copy_is_independent() -> None:
    """La copie d'une grille est indépendante de l'originale."""
    grid = random_grid(6, 6, 0.2, seed=3)
    clone = grid.copy()
    clone.blocked[0] = 1
    assert grid.blocked[0] == 0


def check_metrics_are_consistent() -> None:
    """Les métriques exposées (temps, coût, ouverture max) sont cohérentes."""
    grid = random_grid(20, 20, 0.2, seed=1)
    first = astar(grid, 0, grid.size - 1, mode="4")
    second = astar(grid, 0, grid.size - 1, mode="4")
    assert first.explored == second.explored, "la recherche doit être déterministe"
    assert abs(first.cost - second.cost) < EPS
    assert math.isfinite(first.time_ms)
    assert 1 <= first.max_open <= grid.size


# ------------------------------------------------------------------ exécution


def all_checks() -> list[tuple[str, Callable[[], None]]]:
    """Liste ordonnée des contrôles (nom lisible, fonction)."""
    return [
        ("Tous les algorithmes trouvent un chemin valide", check_all_algorithms_find_a_path),
        ("Aucun chemin si l'arrivée est bloquée", check_no_path_when_goal_is_blocked),
        ("Aucun chemin si la carte est coupée en deux", check_no_path_when_disconnected),
        ("A* retrouve le coût de Dijkstra", check_astar_matches_dijkstra),
        ("BFS optimal en 4-voisins, non optimal en 8-voisins", check_bfs_optimality),
        ("DFS produit des chemins plus longs que BFS", check_dfs_path_is_longer),
        ("A* explore moins de cases que Dijkstra", check_astar_explores_less_than_dijkstra),
        ("Greedy explore peu mais n'est pas optimal", check_greedy_is_fast_but_not_optimal),
        ("A* pondéré respecte la borne x w", check_weighted_astar_is_bounded),
        ("Anytime A* converge vers l'optimum", check_anytime_astar_converges),
        ("Anytime A* respecte le budget", check_anytime_astar_respects_budget),
        ("Anytime A* améliore avec un budget plus large", check_anytime_astar_improves_with_budget),
        ("D* Lite retrouve le même chemin qu'A*", check_dstar_lite_matches_astar),
        ("D* Lite suit le déplacement du robot", check_dstar_lite_follows_robot),
        ("D* Lite replanifie plus vite qu'A*", check_dstar_lite_is_faster_to_replan),
        ("Admissibilité des heuristiques", check_heuristics_admissibility),
        ("Règle anti-coins", check_anti_corner_rule),
        ("Manhattan n'est pas optimale en 8-voisins", check_manhattan_is_not_optimal_in_eight),
        ("Coût des chemins et reconstruction", check_path_cost_and_reconstruction),
        ("Copie de grille indépendante", check_grid_copy_is_independent),
        ("Cohérence des métriques", check_metrics_are_consistent),
    ]


def main(argv: list[str] | None = None) -> int:
    """Lance tous les contrôles et renvoie 0 (succès) ou 1 (échec)."""
    checks = all_checks()
    print(f"Auto-contrôle du projet — {len(checks)} vérifications\n" + "-" * 62)
    failures: list[tuple[str, str]] = []
    for label, check in checks:
        try:
            check()
        except AssertionError as exc:
            failures.append((label, str(exc) or "échec de l'assertion"))
            print(f"  ECHEC  {label}")
            print(f"         -> {failures[-1][1]}")
        except Exception:  # pragma: no cover - garde-fou
            failures.append((label, traceback.format_exc(limit=2)))
            print(f"  ERREUR {label}")
        else:
            print(f"  ok     {label}")
    print("-" * 62)
    if failures:
        print(f"{len(failures)} contrôle(s) en échec sur {len(checks)}.")
        return 1
    print(f"Tous les contrôles sont passés ({len(checks)}/{len(checks)}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
