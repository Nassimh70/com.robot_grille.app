"""
Robot sur grille — navigation, algorithmes de recherche et comparaison.

Paquet du projet académique « Navigation d'un robot sur grille ».

Modules
-------
``src.grid``        modèle de la grille (cases, obstacles, voisins, coûts)
``src.heuristics``  heuristiques admissibles (Manhattan, Euclidienne, Octile, Chebyshev)
``src.result``      structure commune de retour des algorithmes
``src.algorithms``  BFS, DFS, Dijkstra, A*, Greedy, A* pondéré, Anytime A*, D* Lite
``src.benchmark``   protocole expérimental (``python -m src.benchmark``)
``src.app``         interface graphique (niveaux 1, 2 et 3)
"""

__all__ = ["grid", "heuristics", "result", "algorithms", "benchmark", "app"]
__version__ = "1.0.0"
