"""
controller/app_controller.py
Головне вікно застосунку та контролер MVC.
"""

from __future__ import annotations
import random
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

import matplotlib
matplotlib.use("TkAgg")

from model.problem import ProblemInstance, SolderPoint
from model.algorithms import solve_greedy, solve_aco, AcoParams
from view.task_tab import TaskTab
from view.exp_tab import ExpTab

DEFAULT_POINTS = [
    (25, 40, 35), (55, 15, 45), (80, 65, 40),
    (15, 85, 30), (95, 30, 50), (45, 90, 20),
]
DEFAULT_Q   = 100
DEFAULT_TAU = 8
DEFAULT_V   = 15


class AppController(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Маршрут пайки — Танчук / Міхрін / Моріна")
        self.geometry("1200x750")
        self.resizable(True, True)
        self.configure(bg="#ecf0f1")

        self._task: Optional[ProblemInstance] = None
        self._build_ui()
        self._load_default()

    def _build_ui(self) -> None:
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        self.task_tab = TaskTab(nb, on_solve=self._on_solve)
        self.exp_tab  = ExpTab(nb,  on_run=self._on_run_experiment)

        nb.add(self.task_tab, text="  Індивідуальна задача  ")
        nb.add(self.exp_tab,  text="  Експерименти  ")

    def _load_default(self) -> None:
        pts = [SolderPoint(x, y, q) for x, y, q in DEFAULT_POINTS]
        self.task_tab.load_points(pts, DEFAULT_Q, DEFAULT_TAU, DEFAULT_V)

    def _on_solve(self, mode: str) -> None:
        task = self.task_tab.get_task()
        if task is None:
            return
        self._task = task

        aco_params = None
        if mode in ("aco", "both"):
            aco_params = self.task_tab.get_aco_params()
            if aco_params is None:
                return

        try:
            greedy = solve_greedy(task) if mode in ("greedy", "both") else None
            aco = solve_aco(task, aco_params) if mode in ("aco", "both") else None
        except Exception as exc:
            messagebox.showerror("Помилка виконання", str(exc))
            return

        self.task_tab.show_result(greedy, aco)
        self.task_tab.draw_solutions(task, greedy, aco)

    def _on_run_experiment(self, params: dict) -> None:
        thread = threading.Thread(
            target=self._experiment_worker, args=(params,), daemon=True
        )
        thread.start()

    def _experiment_worker(self, params: dict) -> None:
        series = params.get("series", "all")

        if series in ("all", 1):
            self._run_series1(params)
        if series in ("all", 2):
            self._run_series2(params)
        if series in ("all", 3):
            self._run_series3(params)

        self.after(0, self.exp_tab.set_progress, 100, "Готово!")

    # ── Серія 1: вплив розмірності n ────────────────────────────

    def _run_series1(self, params: dict) -> None:
        aco_params = AcoParams(
            m=params["aco_m"],
            n_iter=params["aco_n_iter"],
            alpha=params["aco_alpha"],
            beta=params["aco_beta"],
            rho=params["aco_rho"],
            stagnation_limit=params["aco_k"],
        )

        ns = list(range(params["n_from"], params["n_to"] + 1, params["n_step"]))
        total_runs = len(ns) * params["count"]
        done = 0
        results = []

        for n in ns:
            devs, tg_list, ta_list = [], [], []
            for seed in range(params["count"]):
                task = self._make_task(n, params, seed)

                g = solve_greedy(task)
                tg_list.append(g.algo_time * 1000)

                a = solve_aco(task, AcoParams(
                    m=aco_params.m, n_iter=aco_params.n_iter,
                    alpha=aco_params.alpha, beta=aco_params.beta,
                    rho=aco_params.rho,
                    stagnation_limit=aco_params.stagnation_limit,
                    seed=seed * 1000 + n,
                ))
                ta_list.append(a.algo_time * 1000)

                if g.total_time > 0:
                    devs.append((g.total_time - a.total_time) / g.total_time * 100)

                done += 1
                pct = done / total_runs * 100
                self.after(0, self.exp_tab.set_progress, pct,
                           f"С1: n={n}, задача {seed+1}/{params['count']}  ({pct:.0f}%)")

            avg_tg = sum(tg_list) / len(tg_list) if tg_list else 0.0
            avg_ta = sum(ta_list) / len(ta_list) if ta_list else 0.0
            avg_d  = sum(devs) / len(devs) if devs else None
            max_d  = max(devs) if devs else None
            row = (n, avg_tg, avg_ta, avg_d, max_d)
            results.append(row)
            self.after(0, self.exp_tab.add_row1, row)

        self.exp_tab.set_results(results)
        self.after(0, self.exp_tab.draw_charts1, results)
        self.after(0, self.exp_tab.set_progress, 33, "Серія 1 завершена")

    # ── Серія 2: визначення параметра умови завершення K ────────

    def _run_series2(self, params: dict) -> None:
        n        = params["n_fixed"]
        n_tasks  = params["k_tasks"]
        i_max    = params["k_itermax"]

        # Запускаємо кожну задачу з великою кількістю ітерацій,
        # на кожній ітерації фіксуємо поточний рекорд T*.
        # best_by_iter[iter] = список рекордів по всіх задачах
        best_by_iter: dict[int, list] = {i: [] for i in range(1, i_max + 1)}

        total = n_tasks
        for seed in range(n_tasks):
            task = self._make_task(n, params, seed)
            best_z = float("inf")
            best_history = []   # best_z після кожної ітерації

            # Запускаємо ACO вручну ітерацію за ітерацією
            p = AcoParams(
                m=params["aco_m"],
                n_iter=1,          # по одній ітерації
                alpha=params["aco_alpha"],
                beta=params["aco_beta"],
                rho=params["aco_rho"],
                stagnation_limit=0,  # без зупинки
                seed=seed * 777,
            )
            size = len(task.points) + 1
            # Ініціалізуємо феромон вручну
            import math
            nonzero = [task.dist[i][j] for i in range(size)
                       for j in range(size) if i != j and task.dist[i][j] > 0]
            mean_d = sum(nonzero) / len(nonzero) if nonzero else 1.0
            tau0 = 1.0 / (len(task.points) * mean_d) if task.points else 1.0

            from model.algorithms import _build_route_ant, _deposit_pheromone
            import random as rnd_mod
            rng = rnd_mod.Random(seed * 777)
            tau = [[tau0 if i != j else 0.0 for j in range(size)]
                   for i in range(size)]
            eta = [[0.0] * size for _ in range(size)]
            for i in range(size):
                for j in range(size):
                    if i != j and task.dist[i][j] > 0:
                        eta[i][j] = 1.0 / task.dist[i][j]

            for it in range(1, i_max + 1):
                iter_best_z = float("inf")
                iter_best_routes = []
                for _ in range(p.m):
                    routes, z = _build_route_ant(
                        task, tau, eta, p.alpha, p.beta, rng)
                    if z < iter_best_z:
                        iter_best_z, iter_best_routes = z, routes
                    if z < best_z:
                        best_z = z

                # Випаровування
                for i in range(size):
                    for j in range(size):
                        if i != j:
                            tau[i][j] *= (1.0 - p.rho)
                # Підсилення
                if iter_best_routes and iter_best_z < float("inf"):
                    _deposit_pheromone(tau, iter_best_routes, 1.0 / iter_best_z)

                best_history.append(best_z)

            for it, bz in enumerate(best_history, 1):
                best_by_iter[it].append(bz)

            pct = (seed + 1) / total * 100
            self.after(0, self.exp_tab.set_progress, pct,
                       f"С2: задача {seed+1}/{total}  ({pct:.0f}%)")

        # Усереднення по задачах
        results2 = []
        # Показуємо кожну 5-ту ітерацію щоб не перевантажувати таблицю
        step = max(1, i_max // 100)
        for it in range(1, i_max + 1, step):
            vals = best_by_iter.get(it, [])
            if vals:
                avg = sum(vals) / len(vals)
                results2.append((it, avg))
                self.after(0, self.exp_tab.add_row2, (it, avg))

        self.after(0, self.exp_tab.draw_charts2, results2)
        self.after(0, self.exp_tab.set_progress, 66, "Серія 2 завершена")

    # ── Серія 3: вплив α та β ───────────────────────────────────

    def _run_series3(self, params: dict) -> None:
        n       = params["n_fixed"]
        n_tasks = params["ab_tasks"]
        combos  = [(a, b) for a in [1, 2, 3] for b in [1, 2, 3]]
        total   = len(combos) * n_tasks
        done    = 0
        results3 = []

        for alpha, beta in combos:
            devs = []
            for seed in range(n_tasks):
                task = self._make_task(n, params, seed)

                g = solve_greedy(task)
                a = solve_aco(task, AcoParams(
                    m=params["aco_m"],
                    n_iter=params["aco_n_iter"],
                    alpha=alpha,
                    beta=beta,
                    rho=params["aco_rho"],
                    stagnation_limit=params["aco_k"],
                    seed=seed * 333,
                ))
                if g.total_time > 0:
                    devs.append(
                        (g.total_time - a.total_time) / g.total_time * 100
                    )
                done += 1
                pct = done / total * 100
                self.after(0, self.exp_tab.set_progress, pct,
                           f"С3: α={alpha} β={beta}, задача {seed+1}/{n_tasks}  ({pct:.0f}%)")

            avg_d = sum(devs) / len(devs) if devs else 0.0
            row3 = (float(alpha), float(beta), avg_d)
            results3.append(row3)
            self.after(0, self.exp_tab.add_row3, row3)

        self.after(0, self.exp_tab.draw_charts3, results3)
        self.after(0, self.exp_tab.set_progress, 100, "Серія 3 завершена")

    # ── Допоміжний метод генерації задачі ───────────────────────

    def _make_task(self, n: int, params: dict, seed: int) -> ProblemInstance:
        rng = random.Random(seed * 1000 + n)
        pts = [
            SolderPoint(
                round(rng.uniform(0, 100), 2),
                round(rng.uniform(0, 100), 2),
                round(rng.uniform(params["q_lo"],
                                  min(params["q_hi"], params["Q"])), 2),
            )
            for _ in range(n)
        ]
        task = ProblemInstance(points=pts, Q=params["Q"],
                               tau=params["tau"], v=params["v"])
        task.build_dist()
        return task
