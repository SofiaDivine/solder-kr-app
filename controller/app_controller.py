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
        aco_params = AcoParams(
            m=params["aco_m"],
            n_iter=params["aco_n_iter"],
            alpha=params["aco_alpha"],
            beta=params["aco_beta"],
            rho=params["aco_rho"],
        )

        ns = list(range(params["n_from"], params["n_to"] + 1, params["n_step"]))
        total_runs = len(ns) * params["count"]
        done = 0
        results = []

        for n in ns:
            devs, tg_list, ta_list = [], [], []
            for seed in range(params["count"]):
                rng = random.Random(seed * 1000 + n)
                pts = [
                    SolderPoint(
                        round(rng.uniform(0, 100), 2),
                        round(rng.uniform(0, 100), 2),
                        round(rng.uniform(params["q_lo"], min(params["q_hi"], params["Q"])), 2),
                    )
                    for _ in range(n)
                ]
                task = ProblemInstance(points=pts, Q=params["Q"], tau=params["tau"], v=params["v"])
                task.build_dist()

                g = solve_greedy(task)
                tg_list.append(g.algo_time * 1000)

                a = solve_aco(
                    task,
                    AcoParams(
                        m=aco_params.m,
                        n_iter=aco_params.n_iter,
                        alpha=aco_params.alpha,
                        beta=aco_params.beta,
                        rho=aco_params.rho,
                        seed=seed * 1000 + n,
                    ),
                )
                ta_list.append(a.algo_time * 1000)

                if g.total_time > 0:
                    devs.append((g.total_time - a.total_time) / g.total_time * 100)

                done += 1
                pct = done / total_runs * 100
                self.after(
                    0, self.exp_tab.set_progress, pct,
                    f"n={n}, задача {seed + 1}/{params['count']}  ({pct:.0f}%)",
                )

            avg_tg = sum(tg_list) / len(tg_list) if tg_list else 0.0
            avg_ta = sum(ta_list) / len(ta_list) if ta_list else 0.0
            avg_d  = sum(devs) / len(devs) if devs else None
            max_d  = max(devs) if devs else None
            row = (n, avg_tg, avg_ta, avg_d, max_d)
            results.append(row)
            self.after(0, self.exp_tab.add_row, row)

        self.exp_tab.set_results(results)
        self.after(0, self.exp_tab.draw_charts, results)
        self.after(0, self.exp_tab.set_progress, 100, "Готово!")
