r"""
Protocole expérimental de comparaison des algorithmes.

Lancement::

    python -m src.benchmark              # campagne complète, écrit RESULTATS.md
    python -m src.benchmark --quick      # campagne rapide (débogage)
    python -m src.benchmark --reps 50    # plus de répétitions

Le protocole (cf. § 7 du document de projet) :

* **tailles** : 20×20, 50×50, 100×100 ;
* **densités d'obstacles** : 10 %, 20 %, 30 % ;
* **modes** : 4-voisins et 8-voisins ;
* **répétitions** : 30 grilles aléatoires par combinaison, avec une graine
  fixée et **les mêmes instances pour tous les algorithmes** ;
* **mesure du temps** : une exécution de chauffe, puis ``time.perf_counter()``
  autour de la recherche uniquement ;
* **agrégation** : moyenne, médiane et écart-type ;
* **replanification** : 100 modifications d'obstacles aléatoires, comparaison
  « A\* depuis zéro » et « D\* Lite ».

Trois métriques sont relevées pour chaque algorithme :

===================== =======================================================
Temps de calcul        durée de la recherche seule, en ms (affichage exclu)
Longueur du chemin     somme des coûts des arêtes du chemin trouvé
Cases explorées        nombre de sommets extraits de la liste ouverte
===================== =======================================================
"""

from __future__ import annotations

import argparse
import random
import statistics
import time
from dataclasses import dataclass, field

from .algorithms import ALGORITHMS
from .algorithms.dstar_lite import DStarLite
from .algorithms.astar import astar
from .grid import Grid

#: Tailles testées.
SIZES: tuple[tuple[int, int], ...] = ((20, 20), (50, 50), (100, 100))

#: Densités d'obstacles testées.
DENSITIES: tuple[float, ...] = (0.10, 0.20, 0.30)

#: Modes de déplacement testés.
MODES: tuple[str, ...] = ("4", "8")

#: Nombre de répétitions par combinaison.
REPETITIONS = 30

#: Graine de base : fixe et reproductible.
BASE_SEED = 20240501


# --------------------------------------------------------------------- outils


def make_grid(rows: int, cols: int, density: float, seed: int) -> Grid:
    """Crée une grille aléatoire de densité donnée.

    Le départ (coin haut-gauche) et l'arrivée (coin bas-droit) sont toujours
    laissés libres.
    """
    rng = random.Random(seed)
    grid = Grid(rows, cols)
    for cell in range(grid.size):
        if rng.random() < density:
            grid.blocked[cell] = 1
    grid.blocked[0] = 0
    grid.blocked[grid.size - 1] = 0
    return grid


def _pick_endpoints(grid: Grid, rng: random.Random) -> tuple[int, int] | None:
    """Choisit un couple (départ, arrivée) libre et connecté, ou ``None``.

    On privilégie les **deux coins opposés** (coin haut-gauche et coin
    bas-droit) : c'est le protocole classique de la navigation sur grille, et
    il donne des trajets longs, donc des mesures significatives. Si ces coins
    ne sont pas reliés (obstacle qui isole la carte), on retombe sur un
    couple de cases libres connectées.
    """
    start, goal = 0, grid.size - 1
    if grid.is_reachable(start, goal, "4"):
        return start, goal

    free = grid.free_cells()
    if len(free) < 2:
        return None
    rng.shuffle(free)
    for candidate in free[:40]:
        for other in free[:40]:
            if candidate == other:
                continue
            if grid.is_reachable(candidate, other, "4"):
                return candidate, other
    return None


def build_instances(
    rows: int,
    cols: int,
    density: float,
    mode: str,
    repetitions: int,
    seed: int = BASE_SEED,
) -> list[tuple[Grid, int, int]]:
    """Construit les instances de test (identiques pour tous les algorithmes)."""
    instances: list[tuple[Grid, int, int]] = []
    rng = random.Random(seed ^ (rows * 1000 + cols * 10 + int(density * 100)))
    attempt = 0
    while len(instances) < repetitions and attempt < repetitions * 50:
        attempt += 1
        grid = make_grid(rows, cols, density, seed + attempt * 7919)
        endpoints = _pick_endpoints(grid, rng)
        if endpoints is None:
            continue
        start, goal = endpoints
        instances.append((grid, start, goal))
    return instances


@dataclass
class Stats:
    """Agrégats d'une série de mesures."""

    count: int = 0
    successes: int = 0
    times: list[float] = field(default_factory=list)
    costs: list[float] = field(default_factory=list)
    explored: list[int] = field(default_factory=list)
    max_open: list[int] = field(default_factory=list)

    def add(self, found: bool, time_ms: float, cost: float, explored: int, max_open: int) -> None:
        self.count += 1
        if found:
            self.successes += 1
            self.times.append(time_ms)
            self.costs.append(cost)
            self.explored.append(explored)
            self.max_open.append(max_open)

    @property
    def success_rate(self) -> float:
        return self.successes / self.count if self.count else 0.0

    def mean(self, values: list) -> float:
        return statistics.fmean(values) if values else float("nan")

    def median(self, values: list) -> float:
        return statistics.median(values) if values else float("nan")

    def stdev(self, values: list) -> float:
        return statistics.stdev(values) if len(values) > 1 else 0.0


def warm_up() -> None:
    """Exécution de chauffe (mise en route de l'interpréteur et des caches)."""
    grid = make_grid(20, 20, 0.2, seed=1)
    grid.blocked[5] = 1
    astar(grid, 0, grid.size - 1, "4")


# ------------------------------------------------------------------ campagne


def run_campaign(
    sizes: tuple[tuple[int, int], ...] = SIZES,
    densities: tuple[float, ...] = DENSITIES,
    modes: tuple[str, ...] = MODES,
    repetitions: int = REPETITIONS,
    algorithms: tuple[str, ...] = tuple(ALGORITHMS),
    seed: int = BASE_SEED,
    verbose: bool = True,
) -> dict:
    """Exécute la campagne complète et renvoie les résultats agrégés."""
    warm_up()
    results: dict = {"main": [], "replan": None, "params": {
        "sizes": sizes, "densities": densities, "modes": modes,
        "repetitions": repetitions, "seed": seed, "algorithms": list(algorithms),
    }}
    #: Contrôle de validité : (nombre de chemins vérifiés, nombre d'anomalies).
    validation = {"checked": 0, "invalid": 0, "samples": []}

    for rows, cols in sizes:
        for density in densities:
            for mode in modes:
                instances = build_instances(rows, cols, density, mode, repetitions, seed)
                if verbose:
                    print(
                        f"  {rows}x{cols} · {density:.0%} d'obstacles · {mode}-voisins "
                        f"· {len(instances)} instances",
                        flush=True,
                    )
                per_algorithm: dict[str, Stats] = {}
                for algo_name in algorithms:
                    func = ALGORITHMS[algo_name]
                    stats = Stats()
                    for grid, start, goal in instances:
                        result = func(grid, start, goal, mode=mode, heuristic="auto")
                        stats.add(
                            result.found,
                            result.time_ms,
                            result.cost,
                            result.explored,
                            result.max_open,
                        )
                        # Chaque chemin produit est contrôlé (obstacles traversés,
                        # déplacements illégaux, règle anti-coins, extrémités).
                        if result.found:
                            validation["checked"] += 1
                            problems = grid.validate_path(result.path, start, goal, mode)
                            if problems:
                                validation["invalid"] += 1
                                if len(validation["samples"]) < 5:
                                    validation["samples"].append(
                                        f"{algo_name} ({rows}×{cols}, {mode}-voisins) : "
                                        + "; ".join(problems[:3])
                                    )
                    per_algorithm[algo_name] = stats
                results["main"].append(
                    {
                        "rows": rows,
                        "cols": cols,
                        "density": density,
                        "mode": mode,
                        "instances": len(instances),
                        "stats": per_algorithm,
                    }
                )
    results["validation"] = validation
    if verbose:
        print(
            f"  contrôle des chemins : {validation['checked']} chemins vérifiés · "
            f"{validation['invalid']} invalide(s)",
            flush=True,
        )
    return results


def run_replan_experiment(
    rows: int = 100,
    cols: int = 100,
    density: float = 0.20,
    mode: str = "8",
    changes: int = 100,
    seed: int = BASE_SEED,
    verbose: bool = True,
) -> dict:
    r"""Compare « A\* depuis zéro » et « D\* Lite » sur 100 modifications.

    À chaque modification d'obstacle, on mesure :

    * le temps de la replanification **complète** (A\\* relancé de zéro) ;
    * le temps de la replanification **incrémentale** (D\\* Lite) ;
    * le nombre de cases explorées dans chaque cas.
    """
    rng = random.Random(seed)
    grid = make_grid(rows, cols, density, seed)
    endpoints = _pick_endpoints(grid, rng)
    if endpoints is None:
        return {}
    start, goal = endpoints

    planner = DStarLite(grid, start, goal, mode=mode, heuristic="auto")
    planner.replan()

    astar_times: list[float] = []
    astar_explored: list[int] = []
    dstar_times: list[float] = []
    dstar_explored: list[int] = []
    dstar_costs: list[float] = []
    astar_costs: list[float] = []
    mismatches = 0
    invalid_paths = 0
    checked_paths = 0

    candidates = [c for c in grid.free_cells() if c not in (start, goal)]
    rng.shuffle(candidates)

    toggle = True
    for index in range(changes):
        cell = candidates[index % len(candidates)]
        blocked = toggle
        toggle = not toggle

        # 1. A* depuis zéro
        grid.set_blocked(cell, blocked)
        t0 = time.perf_counter()
        result = astar(grid, start, goal, mode=mode, heuristic="auto")
        astar_times.append((time.perf_counter() - t0) * 1000.0)
        astar_explored.append(result.explored)
        astar_costs.append(result.cost if result.found else float("nan"))

        # 2. D* Lite (incrémental)
        planner.set_blocked(cell, blocked)
        dresult = planner.replan()
        dstar_times.append(dresult.time_ms)
        dstar_explored.append(dresult.explored)
        dstar_costs.append(dresult.cost if dresult.found else float("nan"))

        if result.found != dresult.found or (
            result.found and abs(result.cost - dresult.cost) > 1e-6
        ):
            mismatches += 1

        # 3. Contrôle de validité des deux chemins.
        for candidate in (result, dresult):
            if not candidate.found:
                continue
            checked_paths += 1
            if grid.validate_path(candidate.path, start, goal, mode):
                invalid_paths += 1

    if verbose:
        print(
            f"  replanification : {changes} modifications · "
            f"A* moyen {statistics.fmean(astar_times):.2f} ms · "
            f"D* Lite moyen {statistics.fmean(dstar_times):.2f} ms · "
            f"écarts de coût : {mismatches}",
            flush=True,
        )

    return {
        "rows": rows,
        "cols": cols,
        "density": density,
        "mode": mode,
        "changes": changes,
        "astar": astar_times,
        "astar_explored": astar_explored,
        "astar_costs": astar_costs,
        "dstar": dstar_times,
        "dstar_explored": dstar_explored,
        "dstar_costs": dstar_costs,
        "mismatches": mismatches,
        "checked_paths": checked_paths,
        "invalid_paths": invalid_paths,
    }


# ------------------------------------------------------------------ rapport


def _fmt(value: float, digits: int = 2) -> str:
    if value != value:  # NaN
        return "—"
    return f"{value:.{digits}f}"


def _fmt_int(value: float) -> str:
    if value != value:
        return "—"
    return f"{int(round(value))}"


def render_markdown(results: dict) -> str:
    """Produit le contenu Markdown du fichier ``RESULTATS.md``."""
    lines: list[str] = []
    params = results["params"]
    lines.append("# Résultats expérimentaux")
    lines.append("")
    lines.append(
        "Ce fichier est **généré automatiquement** par `python -m src.benchmark`."
    )
    lines.append("")
    lines.append("## 1. Protocole")
    lines.append("")
    lines.append(
        f"- Tailles : {', '.join(f'{r}×{c}' for r, c in params['sizes'])}"
    )
    lines.append(
        f"- Densités d'obstacles : {', '.join(f'{d:.0%}' for d in params['densities'])}"
    )
    lines.append(f"- Modes : {', '.join(f'{m}-voisins' for m in params['modes'])}")
    lines.append(f"- Répétitions : {params['repetitions']} grilles par combinaison")
    lines.append(f"- Graine de base : `{params['seed']}`")
    lines.append(
        "- Les **mêmes instances** (grilles, départ, arrivée) sont utilisées pour tous les algorithmes."
    )
    lines.append(
        "- Départ et arrivée : **coins opposés** de la grille (haut-gauche → bas-droit) ; "
        "si ces coins sont séparés par les obstacles, un autre couple de cases connectées "
        "est choisi. Les instances retenues sont donc toujours **connexes**."
    )
    lines.append(
        "- Le temps mesuré est celui de la **recherche seule** (`time.perf_counter()`), "
        "affichage exclu ; une exécution de chauffe précède la campagne."
    )
    lines.append(
        "- **Longueur du chemin** = coût réel du trajet (diagonale = √2 en 8-voisins), "
        "quelle que soit la métrique optimisée par l'algorithme."
    )
    lines.append("")
    lines.append("## 2. Résultats principaux")
    lines.append("")
    lines.append(
        "Moyennes sur toutes les instances. Le détail par taille/densité/mode figure "
        "en section 4."
    )
    lines.append("")

    global_stats: dict[str, Stats] = {name: Stats() for name in params["algorithms"]}
    for block in results["main"]:
        for name, stats in block["stats"].items():
            target = global_stats[name]
            target.count += stats.count
            target.successes += stats.successes
            target.times.extend(stats.times)
            target.costs.extend(stats.costs)
            target.explored.extend(stats.explored)
            target.max_open.extend(stats.max_open)

    lines.append(
        "| Algorithme | Temps moyen (ms) | Temps médian (ms) | Écart-type (ms) "
        "| Longueur moyenne | Cases explorées (moy.) | Ouverture max (moy.) | Taux de succès |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for name in params["algorithms"]:
        stats = global_stats[name]
        lines.append(
            "| {name} | {tm} | {tmed} | {sd} | {cost} | {expl} | {mo} | {rate} |".format(
                name=name,
                tm=_fmt(stats.mean(stats.times)),
                tmed=_fmt(stats.median(stats.times)),
                sd=_fmt(stats.stdev(stats.times)),
                cost=_fmt(stats.mean(stats.costs), 3),
                expl=_fmt_int(stats.mean(stats.explored)),
                mo=_fmt_int(stats.mean(stats.max_open)),
                rate=f"{stats.success_rate:.1%}",
            )
        )
    lines.append("")

    lines.append("## 3. Replanification après modification d'obstacle")
    lines.append("")
    replan = results.get("replan")
    if replan:
        a_times = replan["astar"]
        d_times = replan["dstar"]
        lines.append(
            f"Grille {replan['rows']}×{replan['cols']}, {replan['density']:.0%} d'obstacles, "
            f"{replan['mode']}-voisins, {replan['changes']} modifications successives."
        )
        lines.append("")
        lines.append(
            "| Méthode | Temps moyen (ms) | Temps médian (ms) | Cases explorées (moy.) "
            "| Longueur moyenne |"
        )
        lines.append("|---|---|---|---|---|")
        lines.append(
            "| A\\* depuis zéro | {tm} | {tmed} | {expl} | {cost} |".format(
                tm=_fmt(statistics.fmean(a_times)),
                tmed=_fmt(statistics.median(a_times)),
                expl=_fmt_int(statistics.fmean(replan["astar_explored"])),
                cost=_fmt(
                    statistics.fmean([c for c in replan["astar_costs"] if c == c])
                    if any(c == c for c in replan["astar_costs"])
                    else float("nan"),
                    3,
                ),
            )
        )
        lines.append(
            "| D\\* Lite (incrémental) | {tm} | {tmed} | {expl} | {cost} |".format(
                tm=_fmt(statistics.fmean(d_times)),
                tmed=_fmt(statistics.median(d_times)),
                expl=_fmt_int(statistics.fmean(replan["dstar_explored"])),
                cost=_fmt(
                    statistics.fmean([c for c in replan["dstar_costs"] if c == c])
                    if any(c == c for c in replan["dstar_costs"])
                    else float("nan"),
                    3,
                ),
            )
        )
        lines.append("")
        speedup = (
            statistics.fmean(a_times) / statistics.fmean(d_times)
            if statistics.fmean(d_times) > 0
            else float("nan")
        )
        lines.append(
            f"**Accélération moyenne : ×{_fmt(speedup)}** — "
            f"écarts de coût entre A\\* et D\\* Lite : {replan['mismatches']} / {replan['changes']}."
        )
    else:
        lines.append("_(expérience non exécutée)_")
    lines.append("")

    lines.append("## 4. Détail par configuration")
    lines.append("")
    for block in results["main"]:
        lines.append(
            f"### {block['rows']}×{block['cols']} · {block['density']:.0%} d'obstacles "
            f"· {block['mode']}-voisins ({block['instances']} instances)"
        )
        lines.append("")
        lines.append(
            "| Algorithme | Temps moyen (ms) | Temps médian (ms) | Longueur moyenne "
            "| Cases explorées (moy.) | Taux de succès |"
        )
        lines.append("|---|---|---|---|---|---|")
        for name, stats in block["stats"].items():
            lines.append(
                "| {name} | {tm} | {tmed} | {cost} | {expl} | {rate} |".format(
                    name=name,
                    tm=_fmt(stats.mean(stats.times)),
                    tmed=_fmt(stats.median(stats.times)),
                    cost=_fmt(stats.mean(stats.costs), 3),
                    expl=_fmt_int(stats.mean(stats.explored)),
                    rate=f"{stats.success_rate:.1%}",
                )
            )
        lines.append("")

    lines.append("## 5. Contrôle des tendances attendues")
    lines.append("")
    lines.append(
        "Les tendances prévues par le cahier des charges sont **vérifiées "
        "automatiquement** sur les mesures ci-dessus."
    )
    lines.append("")
    lines.append("| Tendance attendue | Constat | Verdict |")
    lines.append("|---|---|---|")

    def stat(name: str) -> Stats:
        return global_stats[name]

    # 1. A* et Dijkstra doivent trouver le même coût.
    costs_astar = stat("A*").costs
    costs_dijkstra = stat("Dijkstra").costs
    if costs_astar and costs_dijkstra:
        diff = max(abs(a - d) for a, d in zip(costs_astar, costs_dijkstra))
        verdict = "✓" if diff < 1e-6 else "✗"
        lines.append(
            f"| A\\* et Dijkstra trouvent le **même coût** | écart maximal : "
            f"{diff:.2e} | {verdict} |"
        )

    # 2. A* explore moins que BFS et Dijkstra.
    for other in ("BFS", "Dijkstra"):
        a = stat("A*").mean(stat("A*").explored)
        b = stat(other).mean(stat(other).explored)
        lines.append(
            f"| A\\* explore **moins** que {other} | {a:.0f} contre {b:.0f} cases | "
            f"{'✓' if a < b else '✗'} |"
        )

    # 3. Greedy explore le moins, mais son chemin est plus long.
    means = {name: stat(name).mean(stat(name).explored) for name in params["algorithms"]}
    least = min(means, key=means.get)
    lines.append(
        f"| **Greedy** explore le moins de cases | l'algorithme le moins explorant est "
        f"« {least} » ({means['Greedy']:.0f} cases pour Greedy) | "
        f"{'✓' if least == 'Greedy' else '✗'} |"
    )
    optimal = stat("Dijkstra").mean(stat("Dijkstra").costs)
    greedy_cost = stat("Greedy").mean(stat("Greedy").costs)
    lines.append(
        f"| Greedy produit des chemins **plus longs** | {greedy_cost:.2f} contre "
        f"{optimal:.2f} pour l'optimum | {'✓' if greedy_cost >= optimal - 1e-9 else '✗'} |"
    )

    # 4. DFS produit les chemins les plus longs.
    longest = max(
        (name for name in params["algorithms"] if name != "DFS"),
        key=lambda n: stat(n).mean(stat(n).costs),
    )
    dfs_cost = stat("DFS").mean(stat("DFS").costs)
    lines.append(
        f"| **DFS** produit les chemins les **plus longs** | {dfs_cost:.0f} contre "
        f"{stat(longest).mean(stat(longest).costs):.0f} pour « {longest} » | "
        f"{'✓' if dfs_cost >= stat(longest).mean(stat(longest).costs) else '✗'} |"
    )

    # 5. A* pondéré : le coût est au plus w fois l'optimum.
    weighted_key = "A* pondéré (w=2)"
    if weighted_key in params["algorithms"]:
        weighted_cost = stat(weighted_key).mean(stat(weighted_key).costs)
        bound = 2.0 * optimal
        lines.append(
            f"| **A\\* pondéré** reste sous la borne ×2 | {weighted_cost:.2f} contre une "
            f"borne de {bound:.2f} | {'✓' if weighted_cost <= bound + 1e-9 else '✗'} |"
        )

    # 6. Anytime A* converge vers l'optimum.
    anytime_key = "Anytime A*"
    if anytime_key in params["algorithms"]:
        anytime_cost = stat(anytime_key).mean(stat(anytime_key).costs)
        lines.append(
            f"| **Anytime A\\*** converge vers l'optimum | {anytime_cost:.2f} contre "
            f"{optimal:.2f} | "
            f"{'✓' if anytime_cost <= optimal + 1e-6 else '✗'} |"
        )

    # 7. D* Lite est plus rapide qu'A* depuis zéro pour une modification locale.
    if replan:
        speedup = statistics.fmean(replan["astar"]) / statistics.fmean(replan["dstar"])
        lines.append(
            f"| **D\\* Lite** replanifie plus vite qu'**A\\* depuis zéro** | "
            f"×{speedup:.1f} en moyenne | {'✓' if speedup > 1.0 else '✗'} |"
        )
        lines.append(
            f"| D\\* Lite et A\\* trouvent le **même chemin** | "
            f"{replan['mismatches']} écart(s) sur {replan['changes']} modifications | "
            f"{'✓' if replan['mismatches'] == 0 else '✗'} |"
        )
    lines.append("")

    # -- validité des chemins -------------------------------------------------
    validation = results.get("validation") or {}
    checked = validation.get("checked", 0)
    invalid = validation.get("invalid", 0)
    replan_checked = replan.get("checked_paths", 0) if replan else 0
    replan_invalid = replan.get("invalid_paths", 0) if replan else 0
    total_checked = checked + replan_checked
    total_invalid = invalid + replan_invalid
    lines.append("## 6. Contrôle de validité des chemins")
    lines.append("")
    lines.append(
        "Chaque chemin produit par les algorithmes est contrôlé automatiquement : "
        "extrémités correctes, aucun obstacle traversé, tous les déplacements "
        "légaux, **règle anti-coins** respectée en 8-voisins."
    )
    lines.append("")
    lines.append("| Contrôle | Chemins vérifiés | Chemins invalides | Verdict |")
    lines.append("|---|---|---|---|")
    lines.append(
        f"| Campagne (tous algorithmes) | {checked} | {invalid} | "
        f"{'✓' if invalid == 0 else '✗'} |"
    )
    if replan:
        lines.append(
            f"| Expérience de replanification | {replan_checked} | {replan_invalid} | "
            f"{'✓' if replan_invalid == 0 else '✗'} |"
        )
    lines.append(
        f"| **Total** | **{total_checked}** | **{total_invalid}** | "
        f"{'✓' if total_invalid == 0 else '✗'} |"
    )
    lines.append("")
    if validation.get("samples"):
        lines.append("Exemples d'anomalies détectées :")
        lines.append("")
        for sample in validation["samples"]:
            lines.append(f"- {sample}")
        lines.append("")

    lines.append("## 7. Lecture des résultats")
    lines.append("")
    lines.append(
        "- Le **nombre de cases explorées** est la mesure la plus fiable : il ne dépend "
        "pas de la machine. Le temps, lui, dépend de l'implémentation et du matériel."
    )
    lines.append(
        "- A\\* et Dijkstra doivent retrouver **le même coût de chemin** : "
        "un écart signalerait une heuristique non admissible ou un bogue."
    )
    lines.append(
        "- BFS est optimal en 4-voisins, mais **pas en 8-voisins** (il minimise le nombre "
        "d'étapes, pas le coût réel avec des diagonales à √2)."
    )
    lines.append(
        "- Greedy explore très peu mais produit parfois des chemins plus longs ; "
        "DFS produit les chemins les plus longs."
    )
    lines.append(
        "- **D\\* Lite lancé de zéro est plus lent qu'A\\*** : sa recherche va *à rebours*, "
        "depuis la destination, et explore donc une zone centrée sur l'arrivée. Son "
        "intérêt n'est pas la première recherche mais la **replanification** : après une "
        "modification locale, seules les cases impactées sont recalculées (section 3)."
    )
    lines.append(
        "- **A\\* pondéré** et **anytime A\\*** explorent beaucoup moins de cases qu'A\\* "
        "optimal, au prix d'un chemin plus long — A\\* pondéré est borné par le facteur "
        "`w`, l'anytime A\\* l'est par le poids de sa dernière itération réussie."
    )
    lines.append("")
    lines.append(
        "Les sections 5 et 6 constituent l'**auto-contrôle** du projet : elles rejouent "
        "à chaque exécution les invariants de correctness (tendances attendues, "
        "validité de chaque chemin). La commande `python -m src.selfcheck` complète "
        "ce contrôle sur des cas ciblés (admissibilité des heuristiques, règle "
        "anti-coins, budget de l'anytime A\\*…)."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "*Généré par `python -m src.benchmark` — voir `README.md` pour le mode d'emploi.*"
    )
    lines.append("")
    return "\n".join(lines)


# ------------------------------------------------------------------------ CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark des algorithmes de navigation.")
    parser.add_argument("--reps", type=int, default=REPETITIONS, help="nombre de répétitions")
    parser.add_argument("--seed", type=int, default=BASE_SEED, help="graine de base")
    parser.add_argument(
        "--output", default="RESULTATS.md", help="fichier Markdown de sortie"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="campagne réduite (20x20 et 50x50, 10 répétitions) pour un essai rapide",
    )
    parser.add_argument(
        "--no-replan", action="store_true", help="ne pas exécuter l'expérience de replanification"
    )
    args = parser.parse_args(argv)

    sizes = SIZES
    densities = DENSITIES
    repetitions = args.reps
    if args.quick:
        sizes = ((20, 20), (50, 50))
        repetitions = min(repetitions, 10)

    print("Campagne de benchmark…", flush=True)
    t0 = time.perf_counter()
    results = run_campaign(
        sizes=sizes,
        densities=densities,
        repetitions=repetitions,
        seed=args.seed,
    )
    if not args.no_replan:
        print("Expérience de replanification…", flush=True)
        results["replan"] = run_replan_experiment(seed=args.seed)
    total = time.perf_counter() - t0

    markdown = render_markdown(results)
    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(markdown)
    print(f"Terminé en {total:.1f} s — résultats écrits dans {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
