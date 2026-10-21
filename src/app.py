r"""
Interface graphique du projet (tkinter — bibliothèque standard, aucune
dépendance supplémentaire).

L'interface est organisée en **trois niveaux**, conformément au cahier des
charges :

* **Niveau 1 — panorama des algorithmes** : BFS, DFS, Dijkstra, A\* et Greedy
  sont comparés sur la même carte (temps, longueur, cases explorées). Le
  chemin et la zone explorée sont affichés.
* **Niveau 2 — carte dynamique** : A\* est rejoué *en temps réel* dès qu'un
  obstacle modifie le trajet restant ; le robot peut être animé le long du
  chemin.
* **Niveau 3 — recherche sous contrainte et replanification incrémentale** :
  anytime A\* avec budget réglable, A\* pondéré, et D\* Lite comparé à
  « A\* depuis zéro ».

Commandes de la souris
----------------------
* **clic gauche** : poser / retirer un obstacle ;
* **clic droit** : déplacer le robot (départ) ;
* **Maj + clic droit** : déplacer la destination.
"""

from __future__ import annotations

import random
import tkinter as tk
from tkinter import ttk

from .algorithms.anytime import anytime_astar
from .algorithms.astar import astar
from .algorithms.bfs import bfs
from .algorithms.dfs import dfs
from .algorithms.dijkstra import dijkstra
from .algorithms.dstar_lite import DStarLite
from .algorithms.greedy import greedy
from .grid import Grid
from .heuristics import HEURISTIC_LABELS, resolve_heuristic
from .result import SearchResult

# ------------------------------------------------------------------ constantes

#: Taille maximale de la grille dans l'interface (au-delà, l'affichage rame).
MAX_SIDE = 60

#: Palette de l'interface.
COL_BG = "#f4f4f4"
COL_GRID = "#d4d4d4"
COL_FREE = "#ffffff"
COL_BLOCKED = "#454545"
COL_EXPLORED = "#b9d6f2"
COL_PATH = "#ffd24a"
COL_START = "#3cb371"
COL_GOAL = "#e05252"
COL_ROBOT = "#ff8c00"

#: Algorithmes proposés au niveau 1 : nom affiché → fonction.
LEVEL1_ALGORITHMS: dict[str, object] = {
    "BFS": bfs,
    "DFS": dfs,
    "Dijkstra": dijkstra,
    "A*": astar,
    "Greedy": greedy,
}


class GridApp(tk.Tk):
    """Fenêtre principale de l'application."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Projet PA — Theme 2 : navigation sur grille")
        self.geometry("1180x780")
        self.minsize(940, 620)

        # ------------------------------------------------------------- état
        self.grid = Grid(30, 30)
        self.start = 0
        self.goal = self.grid.size - 1
        self.result: SearchResult | None = None
        self.visited: set[int] = set()
        self.path: list[int] = []
        self.robot = 0
        self.mode = tk.StringVar(value="4")
        self.heuristic = tk.StringVar(value="auto")
        self.density = tk.DoubleVar(value=0.2)
        self.auto_replan = tk.BooleanVar(value=True)
        self.speed = tk.DoubleVar(value=12.0)
        self.budget_ms = tk.DoubleVar(value=50.0)
        self.weight = tk.DoubleVar(value=2.0)
        self.replan_count = 0
        self.last_replan_ms = 0.0
        self.last_dstar: SearchResult | None = None
        self.last_astar: SearchResult | None = None
        self.dstar: DStarLite | None = None
        self._anim_after: str | None = None
        self._status = tk.StringVar(value="Clic gauche : obstacle · clic droit : départ · Maj+clic droit : arrivée")

        self._build_widgets()
        self._new_map(rows=30, cols=30)
        self._bind_keys()

    # ------------------------------------------------------------ construction

    def _build_widgets(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:  # pragma: no cover - thème indisponible
            pass
        style.configure("Title.TLabel", font=("Segoe UI", 13, "bold"))
        style.configure("Metric.TLabel", font=("Consolas", 10))

        # -- barre supérieure ------------------------------------------------
        top = ttk.Frame(self, padding=(8, 6))
        top.pack(side="top", fill="x")
        ttk.Label(top, text="Navigation sur grille", style="Title.TLabel").pack(side="left")
        ttk.Button(top, text="Nouvelle carte", command=self._on_new_map).pack(side="left", padx=(16, 4))
        ttk.Button(top, text="Vider", command=self._on_clear_map).pack(side="left", padx=4)
        ttk.Button(top, text="Réinitialiser", command=self._on_reset_map).pack(side="left", padx=4)

        ttk.Label(top, text="  Mode :").pack(side="left")
        ttk.Radiobutton(
            top, text="4 voisins", variable=self.mode, value="4",
            command=self._on_mode_change,
        ).pack(side="left")
        ttk.Radiobutton(
            top, text="8 voisins", variable=self.mode, value="8",
            command=self._on_mode_change,
        ).pack(side="left", padx=(4, 12))

        ttk.Label(top, text="Heuristique :").pack(side="left")
        heur_box = ttk.Combobox(
            top,
            textvariable=self.heuristic,
            values=["auto", "manhattan", "euclidean", "octile", "chebyshev"],
            state="readonly",
            width=11,
        )
        heur_box.pack(side="left")
        heur_box.bind("<<ComboboxSelected>>", lambda _e: self._on_mode_change())

        # -- zone centrale ---------------------------------------------------
        main = ttk.Frame(self, padding=(8, 4))
        main.pack(side="top", fill="both", expand=True)

        self.canvas = tk.Canvas(
            main, bg=COL_BG, highlightthickness=1, highlightbackground="#b0b0b0"
        )
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self._draw())
        self.canvas.bind("<Button-1>", self._on_left_click)
        self.canvas.bind("<Button-3>", self._on_right_click)

        right = ttk.Frame(main, padding=(10, 0))
        right.pack(side="right", fill="y")
        self.tabs = ttk.Notebook(right)
        self.tabs.pack(fill="both", expand=True)
        self._build_tab_level1(ttk.Frame(self.tabs))
        self._build_tab_level2(ttk.Frame(self.tabs))
        self._build_tab_level3(ttk.Frame(self.tabs))
        self.tabs.add(self.tab1, text="Niveau 1")
        self.tabs.add(self.tab2, text="Niveau 2")
        self.tabs.add(self.tab3, text="Niveau 3")

        # -- barre d'état ---------------------------------------------------
        status = ttk.Label(self, textvariable=self._status, padding=(8, 4), anchor="w")
        status.pack(side="bottom", fill="x")

    # --------------------------------------------------------------- niveaux

    def _build_tab_level1(self, frame: ttk.Frame) -> None:
        self.tab1 = frame
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Comparaison des algorithmes", font=("Segoe UI", 10, "bold")).pack(
            anchor="w", pady=(6, 2)
        )
        ttk.Label(
            frame,
            text="Les cinq algorithmes sont joués sur la même carte,\n"
            "puis le chemin de l'algorithme sélectionné est affiché.",
            wraplength=320,
        ).pack(anchor="w")

        self.level1_algo = tk.StringVar(value="A*")
        box = ttk.Frame(frame)
        box.pack(anchor="w", pady=(8, 2))
        ttk.Label(box, text="Algorithme :").pack(side="left")
        combo = ttk.Combobox(
            box, textvariable=self.level1_algo, values=list(LEVEL1_ALGORITHMS),
            state="readonly", width=10,
        )
        combo.pack(side="left", padx=(6, 0))

        ttk.Button(frame, text="Lancer la recherche", command=self._on_run_level1).pack(
            anchor="w", pady=4
        )
        ttk.Button(frame, text="Comparer les 5 algorithmes", command=self._on_compare_level1).pack(
            anchor="w", pady=2
        )

        ttk.Separator(frame).pack(fill="x", pady=8)
        self.level1_metrics = tk.Text(frame, height=10, width=42, font=("Consolas", 9), wrap="none")
        self.level1_metrics.pack(fill="both", expand=True)
        self.level1_metrics.tag_configure("title", font=("Consolas", 9, "bold"))
        self.level1_metrics.tag_configure("ok", foreground="#1a7f37")
        self.level1_metrics.tag_configure("warn", foreground="#b35900")

    def _build_tab_level2(self, ttk_frame: ttk.Frame) -> None:
        self.tab2 = ttk_frame
        ttk_frame.pack(fill="both", expand=True)
        ttk.Label(ttk_frame, text="Carte dynamique", font=("Segoe UI", 10, "bold")).pack(
            anchor="w", pady=(6, 2)
        )
        ttk.Label(
            ttk_frame,
            text="A* est rejoué dès qu'un obstacle modifie le trajet\n"
            "restant : c'est la replanification en temps réel.",
            wraplength=320,
        ).pack(anchor="w")

        ttk.Checkbutton(
            ttk_frame, text="Replanification automatique", variable=self.auto_replan
        ).pack(anchor="w", pady=(8, 2))
        ttk.Button(ttk_frame, text="Rechercher (A*)", command=self._on_run_level2).pack(anchor="w", pady=2)

        ttk.Separator(ttk_frame).pack(fill="x", pady=8)
        ttk.Label(ttk_frame, text="Animation du robot").pack(anchor="w")
        self.anim_button = ttk.Button(ttk_frame, text="Animer", command=self._on_toggle_anim)
        self.anim_button.pack(anchor="w", pady=2)
        ttk.Label(ttk_frame, text="Vitesse (pas/s)").pack(anchor="w", pady=(6, 0))
        ttk.Scale(
            ttk_frame, from_=2, to=60, variable=self.speed, orient="horizontal",
            command=lambda _v: None,
        ).pack(fill="x")

        ttk.Separator(ttk_frame).pack(fill="x", pady=8)
        self.level2_metrics = tk.Text(ttk_frame, height=12, width=42, font=("Consolas", 9), wrap="none")
        self.level2_metrics.pack(fill="both", expand=True)
        self.level2_metrics.tag_configure("title", font=("Consolas", 9, "bold"))

    def _build_tab_level3(self, ttk_frame: ttk.Frame) -> None:
        self.tab3 = ttk_frame
        ttk_frame.pack(fill="both", expand=True)
        ttk.Label(ttk_frame, text="Budget et replanification", font=("Segoe UI", 10, "bold")).pack(
            anchor="w", pady=(6, 2)
        )

        ttk.Label(ttk_frame, text="Anytime A* — budget (ms)").pack(anchor="w")
        self.budget_label = ttk.Label(ttk_frame, text="50 ms", style="Metric.TLabel")
        self.budget_label.pack(anchor="w")
        ttk.Scale(
            ttk_frame, from_=1, to=1000, variable=self.budget_ms, orient="horizontal",
            command=self._on_budget_change,
        ).pack(fill="x")
        ttk.Button(ttk_frame, text="Lancer l'anytime A*", command=self._on_run_anytime).pack(
            anchor="w", pady=4
        )

        ttk.Separator(ttk_frame).pack(fill="x", pady=8)
        ttk.Label(ttk_frame, text="A* pondéré — poids w").pack(anchor="w")
        self.weight_label = ttk.Label(ttk_frame, text="w = 2.0", style="Metric.TLabel")
        self.weight_label.pack(anchor="w")
        ttk.Scale(
            ttk_frame, from_=1.0, to=5.0, variable=self.weight, orient="horizontal",
            command=self._on_weight_change,
        ).pack(fill="x")
        ttk.Button(ttk_frame, text="Lancer l'A* pondéré", command=self._on_run_weighted).pack(
            anchor="w", pady=4
        )

        ttk.Separator(ttk_frame).pack(fill="x", pady=8)
        ttk.Label(ttk_frame, text="Replanification incrémentale").pack(anchor="w")
        ttk.Label(
            ttk_frame,
            text="D* Lite réutilise les coûts déjà calculés :\n"
            "touche « D » pour replanifier.",
            wraplength=320,
        ).pack(anchor="w")
        ttk.Button(ttk_frame, text="Replanifier : D* Lite", command=self._on_replan_dstar).pack(
            anchor="w", pady=4
        )
        ttk.Button(ttk_frame, text="Replanifier : A* depuis zéro", command=self._on_replan_astar).pack(
            anchor="w", pady=2
        )

        ttk.Separator(ttk_frame).pack(fill="x", pady=8)
        self.level3_metrics = tk.Text(ttk_frame, height=14, width=42, font=("Consolas", 9), wrap="none")
        self.level3_metrics.pack(fill="both", expand=True)
        self.level3_metrics.tag_configure("title", font=("Consolas", 9, "bold"))
        self.level3_metrics.tag_configure("ok", foreground="#1a7f37")

    # ---------------------------------------------------------------- actions

    def _bind_keys(self) -> None:
        self.bind("<Key-d>", lambda _e: self._on_replan_dstar())
        self.bind("<Key-D>", lambda _e: self._on_replan_dstar())
        self.bind("<Key-a>", lambda _e: self._on_replan_astar())
        self.bind("<Key-r>", lambda _e: self._on_run_level1())
        self.bind("<space>", lambda _e: self._on_toggle_anim())

    def _on_new_map(self) -> None:
        rows = self.grid.rows
        cols = self.grid.cols
        self._new_map(rows=rows, cols=cols)

    def _on_clear_map(self) -> None:
        for i in range(self.grid.size):
            self.grid.blocked[i] = 0
        self.grid.blocked[self.start] = 0
        self.grid.blocked[self.goal] = 0
        self._reset_search()
        self._draw()
        self._set_status("Carte vidée.")

    def _on_reset_map(self) -> None:
        self._new_map(rows=self.grid.rows, cols=self.grid.cols)

    def _new_map(self, rows: int, cols: int) -> None:
        rows = max(5, min(rows, MAX_SIDE))
        cols = max(5, min(cols, MAX_SIDE))
        rng = random.Random()
        self.grid = Grid(rows, cols)
        for cell in range(self.grid.size):
            if rng.random() < self.density.get():
                self.grid.blocked[cell] = 1
        self.start = 0
        self.goal = self.grid.size - 1
        self.grid.blocked[self.start] = 0
        self.grid.blocked[self.goal] = 0
        self.robot = self.start
        self._reset_search()
        self._draw()
        self._set_status(f"Nouvelle carte {rows}×{cols} (obstacles : {self.density.get():.0%}).")

    def _reset_search(self) -> None:
        self.result = None
        self.path = []
        self.visited = set()
        self.replan_count = 0
        self.last_dstar = None
        self.last_astar = None
        self.dstar = None
        self.robot = self.start

    def _on_mode_change(self) -> None:
        name = self.heuristic.get()
        if name != "auto":
            resolved = resolve_heuristic(self.mode.get(), name)
            label = HEURISTIC_LABELS[resolved]
            if resolved != name:
                self._set_status(
                    f"Attention : l'heuristique {label} n'est pas admissible en "
                    f"{self.mode.get()}-voisins — A* ne sera plus optimal."
                )
        self._draw()

    def _on_budget_change(self, value: str) -> None:
        self.budget_label.configure(text=f"{float(value):.0f} ms")

    def _on_weight_change(self, value: str) -> None:
        self.weight_label.configure(text=f"w = {float(value):.1f}")

    # ------------------------------------------------------------- niveau 1

    def _on_run_level1(self) -> None:
        name = self.level1_algo.get()
        func = LEVEL1_ALGORITHMS[name]
        result = func(
            self.grid, self.start, self.goal, mode=self.mode.get(),
            heuristic=self.heuristic.get(),
        )
        self._show_result(result)
        self._write_metrics(self.level1_metrics, self._format_result(result))

    def _on_compare_level1(self) -> None:
        rows = []
        for name, func in LEVEL1_ALGORITHMS.items():
            result = func(
                self.grid, self.start, self.goal, mode=self.mode.get(),
                heuristic=self.heuristic.get(),
            )
            rows.append((name, result))
        # On affiche le chemin de l'algorithme sélectionné.
        selected = self.level1_algo.get()
        for name, result in rows:
            if name == selected:
                self._show_result(result)
                break

        text = self.level1_metrics
        text.delete("1.0", "end")
        text.insert("end", "Algorithme     temps(ms)   coût    explorées\n")
        text.insert("end", "-" * 46 + "\n")
        optimal = None
        for name, result in rows:
            if name == "Dijkstra" and result.found:
                optimal = result.cost
        for name, result in rows:
            if result.found:
                flag = ""
                if optimal is not None and result.cost > optimal + 1e-9:
                    flag = "  (sous-optimal)"
                text.insert(
                    "end",
                    f"{name:<13} {result.time_ms:8.2f} {result.cost:8.2f} "
                    f"{result.explored:8d}{flag}\n",
                )
            else:
                text.insert("end", f"{name:<13} {'—':>8} {'—':>8} {'—':>8}\n")
        text.insert("end", "\n")
        text.insert("end", "A* et Dijkstra doivent trouver le même coût :\n")
        astar_cost = next((r.cost for n, r in rows if n == "A*" and r.found), None)
        dijkstra_cost = next((r.cost for n, r in rows if n == "Dijkstra" and r.found), None)
        if astar_cost is not None and dijkstra_cost is not None:
            same = abs(astar_cost - dijkstra_cost) < 1e-9
            text.insert(
                "end",
                f"A* = {astar_cost:.3f} · Dijkstra = {dijkstra_cost:.3f} → "
                + ("identiques ✓\n" if same else "DIVERGENCE ✗\n"),
                "ok" if same else "warn",
            )
        text.insert("end", "\nMode : ")
        text.insert("end", f"{self.mode.get()}-voisins")
        text.insert("end", "  ·  heuristique : ")
        text.insert("end", resolve_heuristic(self.mode.get(), self.heuristic.get()) + "\n")

    # ------------------------------------------------------------- niveau 2

    def _on_run_level2(self) -> None:
        result = astar(
            self.grid, self.start, self.goal, mode=self.mode.get(),
            heuristic=self.heuristic.get(),
        )
        self._show_result(result)
        self.replan_count = 0
        self._write_metrics(self.level2_metrics, self._format_result(result))

    def _on_toggle_anim(self) -> None:
        if self._anim_after is not None:
            self.after_cancel(self._anim_after)
            self._anim_after = None
            self.anim_button.configure(text="Animer")
            self._set_status("Animation arrêtée.")
            return
        if not self.path:
            self._set_status("Aucun chemin à animer : lancez d'abord une recherche.")
            return
        self.anim_button.configure(text="Arrêter")
        self._set_status("Animation en cours…")
        self._anim_step()

    def _anim_step(self) -> None:
        if not self.path:
            self._anim_after = None
            self.anim_button.configure(text="Animer")
            return
        index = self.path.index(self.robot) if self.robot in self.path else 0
        if index + 1 >= len(self.path):
            self._anim_after = None
            self.anim_button.configure(text="Animer")
            self._set_status("Robot arrivé à destination.")
            return
        self.robot = self.path[index + 1]
        self._draw()
        delay = max(10, int(1000.0 / max(1.0, self.speed.get())))
        self._anim_after = self.after(delay, self._anim_step)

    # ------------------------------------------------------------- niveau 3

    def _on_run_anytime(self) -> None:
        budget = float(self.budget_ms.get())
        result = anytime_astar(
            self.grid, self.start, self.goal, mode=self.mode.get(),
            heuristic=self.heuristic.get(), budget_ms=budget,
        )
        self._show_result(result)
        text = self.level3_metrics
        text.delete("1.0", "end")
        text.insert("end", "Anytime A*\n", "title")
        text.insert("end", f"budget : {budget:.0f} ms\n\n")
        text.insert("end", "  w     coût    temps(ms)  explorées\n")
        text.insert("end", "  " + "-" * 32 + "\n")
        for it in result.extra.get("iterations", ()):
            text.insert(
                "end",
                f"{it['poids']:>4} {it['cout']:>9.2f} {it['temps_ms']:>10.2f} "
                f"{int(it['explores']):>9d}\n",
            )
        text.insert("end", "\n")
        if result.found:
            optimal = result.extra.get("optimal")
            bound = result.extra.get("sous_optimite", float("inf"))
            text.insert(
                "end",
                f"meilleur coût : {result.cost:.3f}\n"
                f"sous-optimalité bornée : ×{bound:.2f}\n",
            )
            if optimal:
                text.insert("end", "optimalité atteinte (w = 1 terminé) ✓\n", "ok")
            else:
                text.insert("end", "budget épuisé avant w = 1 : chemin non optimal\n", "warn")

    def _on_run_weighted(self) -> None:
        weight = float(self.weight.get())
        result = astar(
            self.grid, self.start, self.goal, mode=self.mode.get(),
            heuristic=self.heuristic.get(), weight=weight,
        )
        self._show_result(result)
        text = self.level3_metrics
        text.delete("1.0", "end")
        text.insert("end", f"A* pondéré (w = {weight:.1f})\n", "title")
        text.insert("end", self._format_result(result))
        text.insert("end", "\nLe coût obtenu est au plus w fois l'optimum.\n")

    def _on_replan_dstar(self) -> None:
        """Replanification incrémentale par D\\* Lite."""
        if self.dstar is None:
            self.dstar = DStarLite(
                self.grid, self.start, self.goal, mode=self.mode.get(),
                heuristic=self.heuristic.get(),
            )
        result = self.dstar.replan()
        self.replan_count += 1
        self.last_replan_ms = result.time_ms
        self.last_dstar = result
        self._show_result(result)
        self._write_replan_comparison("D* Lite (incrémental)")

    def _on_replan_astar(self) -> None:
        """Replanification complète : A\\* relancé de zéro."""
        result = astar(
            self.grid, self.start, self.goal, mode=self.mode.get(),
            heuristic=self.heuristic.get(),
        )
        self.replan_count += 1
        self.last_replan_ms = result.time_ms
        self.last_astar = result
        self._show_result(result)
        self._write_replan_comparison("A* depuis zéro")

    def _write_replan_comparison(self, last_label: str) -> None:
        """Affiche côte à côte les deux méthodes de replanification."""
        text = self.level3_metrics
        text.delete("1.0", "end")
        text.insert("end", f"Replanification n° {self.replan_count} — {last_label}\n", "title")
        text.insert("end", "\n")
        for label, result in (("D* Lite (incrémental)", self.last_dstar),
                              ("A* depuis zéro", self.last_astar)):
            if result is None:
                continue
            if result.found:
                text.insert(
                    "end",
                    f"{label:<22} {result.time_ms:7.3f} ms · "
                    f"{result.explored:5d} cases explorées · coût {result.cost:.3f}\n",
                )
            else:
                text.insert("end", f"{label:<22} aucun chemin\n")
        if self.last_dstar and self.last_astar and self.last_dstar.found and self.last_astar.found:
            speedup = (
                self.last_astar.time_ms / self.last_dstar.time_ms
                if self.last_dstar.time_ms > 0
                else float("inf")
            )
            same = abs(self.last_dstar.cost - self.last_astar.cost) < 1e-6
            text.insert("end", "\n")
            text.insert("end", f"accélération D* Lite : ×{speedup:.2f}\n", "ok")
            text.insert(
                "end",
                "coûts identiques : " + ("oui ✓\n" if same else "non ✗\n"),
                "ok" if same else "warn",
            )
        text.insert(
            "end",
            "\nRappel : D* Lite est plus rapide quand la carte a déjà été\n"
            "explorée — son avantage porte sur les replanifications suivantes.\n",
        )

    # ----------------------------------------------------------------- souris

    def _cell_at(self, event: tk.Event) -> int | None:
        size = self._cell_size()
        if size <= 0:
            return None
        ox, oy = self._grid_origin()
        col = int((event.x - ox) // size)
        row = int((event.y - oy) // size)
        if not (0 <= row < self.grid.rows and 0 <= col < self.grid.cols):
            return None
        return row * self.grid.cols + col

    def _on_left_click(self, event: tk.Event) -> None:
        cell = self._cell_at(event)
        if cell is None:
            return
        if cell in (self.start, self.goal):
            self._set_status("Impossible de poser un obstacle sur le départ ou l'arrivée.")
            return
        blocked = not self.grid.blocked[cell]
        self.grid.set_blocked(cell, blocked)
        if self.dstar is not None:
            self.dstar.set_blocked(cell, blocked)
        self._on_map_changed(cell)

    def _on_right_click(self, event: tk.Event) -> None:
        cell = self._cell_at(event)
        if cell is None or self.grid.blocked[cell]:
            return
        if event.state & 0x0001:  # Maj enfoncée → nouvelle destination
            self.goal = cell
            self._set_status(f"Destination déplacée en {divmod(cell, self.grid.cols)}.")
        else:
            self.start = cell
            self.robot = cell
            self._set_status(f"Départ déplacé en {divmod(cell, self.grid.cols)}.")
        self.dstar = None
        self._on_map_changed(cell)

    def _on_map_changed(self, cell: int) -> None:
        """Appelé après toute modification de la carte."""
        self._draw()
        # Les mesures de replanification ne portent plus sur la carte courante.
        self.last_dstar = None
        self.last_astar = None
        if self.tabs.index(self.tabs.select()) != 1:  # niveau 2 uniquement
            return
        if not self.auto_replan.get() or not self.path:
            return
        # On replanifie si le trajet restant est coupé par le changement.
        remaining = self.path[self.path.index(self.robot):] if self.robot in self.path else self.path
        if any(self.grid.blocked[c] for c in remaining):
            result = astar(
                self.grid, self.robot, self.goal, mode=self.mode.get(),
                heuristic=self.heuristic.get(),
            )
            self.replan_count += 1
            self.last_replan_ms = result.time_ms
            self._show_result(result)
            self._write_metrics(
                self.level2_metrics,
                self._format_result(result)
                + f"\nreplanifications : {self.replan_count}\n"
                + f"dernière replanification : {self.last_replan_ms:.3f} ms\n",
            )
            self._set_status("Obstacle sur le trajet : replanification en temps réel.")

    # -------------------------------------------------------------- affichage

    def _cell_size(self) -> float:
        if not self.canvas.winfo_width() or not self.canvas.winfo_height():
            return 0.0
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        return max(1.0, min(width / self.grid.cols, height / self.grid.rows))

    def _grid_origin(self) -> tuple[float, float]:
        size = self._cell_size()
        ox = (self.canvas.winfo_width() - size * self.grid.cols) / 2.0
        oy = (self.canvas.winfo_height() - size * self.grid.rows) / 2.0
        return ox, oy

    def _draw(self) -> None:
        if not self.canvas.winfo_width():
            return
        canvas = self.canvas
        canvas.delete("all")
        size = self._cell_size()
        ox, oy = self._grid_origin()
        cols = self.grid.cols
        path_set = set(self.path)
        robot = self.robot

        for row in range(self.grid.rows):
            for col in range(self.grid.cols):
                cell = row * cols + col
                if self.grid.blocked[cell]:
                    color = COL_BLOCKED
                elif cell in path_set:
                    color = COL_PATH
                elif cell in self.visited:
                    color = COL_EXPLORED
                else:
                    color = COL_FREE
                x0 = ox + col * size
                y0 = oy + row * size
                canvas.create_rectangle(
                    x0, y0, x0 + size, y0 + size,
                    fill=color, outline=COL_GRID, width=0.5,
                )

        # Départ / arrivée / robot.
        sr, sc = divmod(self.start, cols)
        gr, gc = divmod(self.goal, cols)
        canvas.create_oval(
            ox + sc * size + size * 0.15, oy + sr * size + size * 0.15,
            ox + (sc + 1) * size - size * 0.15, oy + (sr + 1) * size - size * 0.15,
            fill=COL_START, outline="",
        )
        canvas.create_oval(
            ox + gc * size + size * 0.15, oy + gr * size + size * 0.15,
            ox + (gc + 1) * size - size * 0.15, oy + (gr + 1) * size - size * 0.15,
            fill=COL_GOAL, outline="",
        )
        if robot not in (self.start, self.goal):
            rr, rc = divmod(robot, cols)
            canvas.create_oval(
                ox + rc * size + size * 0.1, oy + rr * size + size * 0.1,
                ox + (rc + 1) * size - size * 0.1, oy + (rr + 1) * size - size * 0.1,
                fill=COL_ROBOT, outline="white", width=1.5,
            )

        # Tracé du chemin.
        if len(self.path) > 1:
            points = []
            for cell in self.path:
                r, c = divmod(cell, cols)
                points.extend((ox + (c + 0.5) * size, oy + (r + 0.5) * size))
            canvas.create_line(*points, fill="#c98f00", width=max(1.0, size * 0.12),
                               capstyle="round", joinstyle="round")

    def _show_result(self, result: SearchResult) -> None:
        self.result = result
        self.path = list(result.path)
        self.visited = set(result.extra.get("visites", ()))
        self._draw()

    @staticmethod
    def _format_result(result: SearchResult) -> str:
        if not result.found:
            reason = result.extra.get("reason", "")
            return (
                f"algorithme : {result.name}\n"
                f"résultat   : aucun chemin {('(' + reason + ')') if reason else ''}\n"
                f"temps      : {result.time_ms:.3f} ms\n"
                f"explorées  : {result.explored}\n"
            )
        lines = [
            f"algorithme : {result.name}",
            f"résultat   : chemin trouvé",
            f"temps      : {result.time_ms:.3f} ms",
            f"longueur   : {result.cost:.3f} ({result.steps} pas)",
            f"explorées  : {result.explored}",
            f"ouverture  : {result.max_open} (max)",
        ]
        heur = result.extra.get("heuristique")
        if heur:
            lines.append(f"heuristique: {heur}")
        weight = result.extra.get("poids")
        if weight is not None and weight != 1.0:
            lines.append(f"poids      : w = {weight:g}")
        if result.extra.get("interrompu"):
            lines.append("statut     : recherche interrompue (budget)")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _write_metrics(widget: tk.Text, content: str) -> None:
        widget.delete("1.0", "end")
        widget.insert("end", content)

    def _set_status(self, message: str) -> None:
        self._status.set(message)


def main() -> int:
    """Lance l'interface graphique."""
    app = GridApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
