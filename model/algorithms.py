"""
model/algorithms.py
Алгоритми розв'язання задачі маршрутизації паяльної головки.

Реалізовано:
    solve_greedy  — жадібний алгоритм (найближчий сусід + дозаправка)
    solve_aco     — мурашиний алгоритм (ACO) з ресурсним обмеженням
"""

from __future__ import annotations
import random
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .problem import ProblemInstance, Solution


# ══════════════════════════════════════════════════════════════════
# Жадібний алгоритм  O(n²)
# ══════════════════════════════════════════════════════════════════

def solve_greedy(task: ProblemInstance) -> Solution:
    """
    Жадібний алгоритм (евристика найближчого сусіда з ресурсним обмеженням).

    На кожному кроці обирається найближча допустима точка (q_i ≤ залишок припою).
    Якщо таких точок немає — повернення на базу та дозаправка.

    Складність: O(n²).
    """
    t0 = time.perf_counter()
    routes, total = _build_route_greedy(task)
    return Solution(
        routes=routes,
        total_time=total,
        algo_time=time.perf_counter() - t0,
        algo_name="Жадібний",
    )


def _build_route_greedy(task: ProblemInstance) -> Tuple[List[List[int]], float]:
    """Побудова маршруту жадібним правилом найближчого сусіда."""
    n = len(task.points)
    unvisited = set(range(1, n + 1))
    routes: List[List[int]] = []
    total = 0.0

    while unvisited:
        solder = task.Q
        current = 0
        route: List[int] = []
        feasible = {j for j in unvisited if task.points[j - 1].q <= solder}

        while feasible:
            best = min(feasible, key=lambda j: task.dist[current][j])
            total += task.dist[current][best]
            solder -= task.points[best - 1].q
            route.append(best)
            unvisited.discard(best)
            current = best
            feasible = {j for j in unvisited if task.points[j - 1].q <= solder}

        total += task.dist[current][0]
        routes.append(route)
        if unvisited:
            total += task.tau

    return routes, total


# ══════════════════════════════════════════════════════════════════
# Мурашиний алгоритм  O(N_iter · m · n²)
# ══════════════════════════════════════════════════════════════════

@dataclass
class AcoParams:
    """Параметри мурашиного алгоритму (розділ 2.3, 3.3.1)."""
    m: int = 20
    n_iter: int = 100
    alpha: float = 1.0
    beta: float = 2.0
    rho: float = 0.1
    seed: Optional[int] = None
    stagnation_limit: int = 0  # 0 = вимкнено; інакше зупинка після L ітерацій без покращення


def solve_aco(task: ProblemInstance, params: Optional[AcoParams] = None) -> Solution:
    """
    Мурашиний алгоритм (Ant Colony Optimization) з обмеженням на запас припою.

    Кожна мураха будує допустимий маршрут; перехід до наступної точки —
    імовірнісний (феромон τ^α · евристика η^β). При нестачі припою — дозаправка в R.

    Складність: O(N_iter · m · n²), пам'ять O(n²).
    """
    p = params or AcoParams()
    t0 = time.perf_counter()
    rng = random.Random(p.seed)

    n = len(task.points)
    size = n + 1

    # Евристика η_ij = 1 / c_ij
    eta = [[0.0] * size for _ in range(size)]
    for i in range(size):
        for j in range(size):
            if i != j and task.dist[i][j] > 0:
                eta[i][j] = 1.0 / task.dist[i][j]

    # Початковий феромон τ_0
    nonzero = [task.dist[i][j] for i in range(size) for j in range(size) if i != j and task.dist[i][j] > 0]
    mean_dist = sum(nonzero) / len(nonzero) if nonzero else 1.0
    tau0 = 1.0 / (n * mean_dist) if n > 0 else 1.0
    tau = [[tau0 if i != j else 0.0 for j in range(size)] for i in range(size)]

    best_routes: List[List[int]] = []
    best_Z = float("inf")
    no_improve = 0

    for _ in range(p.n_iter):
        iter_best_Z = float("inf")
        iter_best_routes: List[List[int]] = []

        for _ in range(p.m):
            routes, Z = _build_route_ant(task, tau, eta, p.alpha, p.beta, rng)
            if Z < iter_best_Z:
                iter_best_Z, iter_best_routes = Z, routes
            if Z < best_Z:
                best_Z, best_routes = Z, routes
                no_improve = 0

        if iter_best_Z >= best_Z:
            no_improve += 1
        else:
            no_improve = 0

        # Випаровування феромонів
        for i in range(size):
            for j in range(size):
                if i != j:
                    tau[i][j] *= 1.0 - p.rho

        # Підсилення на ребрах найкращої мурахи ітерації
        if iter_best_routes and iter_best_Z < float("inf"):
            deposit = 1.0 / iter_best_Z
            _deposit_pheromone(tau, iter_best_routes, deposit)

        if p.stagnation_limit > 0 and no_improve >= p.stagnation_limit:
            break

    return Solution(
        routes=best_routes,
        total_time=best_Z,
        algo_time=time.perf_counter() - t0,
        algo_name="Мурашиний (ACO)",
    )


def _build_route_ant(
    task: ProblemInstance,
    tau: List[List[float]],
    eta: List[List[float]],
    alpha: float,
    beta: float,
    rng: random.Random,
) -> Tuple[List[List[int]], float]:
    """Побудова одного маршруту мурахою (табл. 2.2, кроки 3.1–3.7)."""
    n = len(task.points)
    unvisited = set(range(1, n + 1))
    routes: List[List[int]] = []
    total = 0.0

    while unvisited:
        solder = task.Q
        current = 0
        route: List[int] = []
        feasible = {j for j in unvisited if task.points[j - 1].q <= solder}

        while feasible:
            j_next = _select_next_ant(current, feasible, tau, eta, alpha, beta, rng)
            total += task.dist[current][j_next]
            solder -= task.points[j_next - 1].q
            route.append(j_next)
            unvisited.discard(j_next)
            current = j_next
            feasible = {j for j in unvisited if task.points[j - 1].q <= solder}

        total += task.dist[current][0]
        routes.append(route)
        if unvisited:
            total += task.tau

    return routes, total


def _select_next_ant(
    current: int,
    feasible: set,
    tau: List[List[float]],
    eta: List[List[float]],
    alpha: float,
    beta: float,
    rng: random.Random,
) -> int:
    """Імовірнісний вибір наступної точки: p_ij ∝ τ^α · η^β."""
    candidates = list(feasible)
    weights = []
    for j in candidates:
        t = tau[current][j] ** alpha
        h = eta[current][j] ** beta
        weights.append(t * h if t > 0 and h > 0 else 1e-12)

    total_w = sum(weights)
    if total_w <= 0:
        return rng.choice(candidates)

    r = rng.random() * total_w
    acc = 0.0
    for j, w in zip(candidates, weights):
        acc += w
        if acc >= r:
            return j
    return candidates[-1]


def _deposit_pheromone(
    tau: List[List[float]],
    routes: List[List[int]],
    deposit: float,
) -> None:
    """Підсилення феромону на ребрах маршруту (включно з переходами через R)."""
    for sub in routes:
        if not sub:
            continue
        path = [0] + sub + [0]
        for a, b in zip(path, path[1:]):
            tau[a][b] += deposit

