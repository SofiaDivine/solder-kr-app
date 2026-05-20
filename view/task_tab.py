"""
view/task_tab.py
Вкладка «Індивідуальна задача»: введення умови, кнопки розв'язання,
відображення результатів і графіків.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Callable

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from .route_canvas import draw_route
from model.problem import ProblemInstance, SolderPoint, Solution
from model.algorithms import AcoParams


class TaskTab(ttk.Frame):
    """
    Фрейм вкладки «Індивідуальна задача».

    Зв'язок з контролером здійснюється через колбеки:
        on_solve(mode)  — виклик при натисканні кнопки розв'язання
    """

    def __init__(self, parent: ttk.Notebook, on_solve: Callable[[str], None]):
        super().__init__(parent)
        self._on_solve = on_solve
        self._build()

    # ── Побудова інтерфейсу ─────────────────────────────────────

    def _build(self) -> None:
        left = ttk.LabelFrame(self, text="Параметри задачі", padding=8)
        left.pack(side="left", fill="y", padx=(6, 4), pady=6)
        self._build_left(left)

        right = ttk.Frame(self)
        right.pack(side="right", fill="both", expand=True, padx=(4, 6), pady=6)
        self._build_right(right)

    def _build_left(self, left: ttk.LabelFrame) -> None:
        gf = ttk.LabelFrame(left, text="Глобальні параметри", padding=6)
        gf.pack(fill="x", pady=(0, 8))
        self.var_Q   = self._entry(gf, "Місткість Q, од.:",   "100", 0)
        self.var_tau = self._entry(gf, "Час дозаправки τ, с:", "8",  1)
        self.var_v   = self._entry(gf, "Швидкість v, мм/с:",  "15",  2)

        af = ttk.LabelFrame(left, text="Параметри ACO", padding=6)
        af.pack(fill="x", pady=(0, 8))
        self.var_m      = self._entry(af, "Мурах m:",        "20",  0)
        self.var_n_iter = self._entry(af, "Ітерації N:",    "100", 1)
        self.var_alpha  = self._entry(af, "α (феромон):",   "1",   2)
        self.var_beta   = self._entry(af, "β (евристика):","2",   3)
        self.var_rho    = self._entry(af, "ρ (випаров.)",   "0.1", 4)

        tf = ttk.LabelFrame(left, text="Точки пайки (X, Y, q)", padding=6)
        tf.pack(fill="both", expand=True)
        cols = ("№", "X, мм", "Y, мм", "q, од.")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings", height=8)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=65, anchor="center")
        sb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        bf = ttk.Frame(left)
        bf.pack(fill="x", pady=4)
        ttk.Button(bf, text="Додати рядок", command=self._add_row).pack(side="left", padx=2)
        ttk.Button(bf, text="Видалити",     command=self._del_row).pack(side="left", padx=2)
        ttk.Button(bf, text="Очистити",     command=self.clear_rows).pack(side="left", padx=2)

        ief = ttk.Frame(left)
        ief.pack(fill="x", pady=2)
        ttk.Button(ief, text="Імпорт JSON",  command=self._import_json).pack(side="left", padx=2)
        ttk.Button(ief, text="Експорт JSON", command=self._export_json).pack(side="left", padx=2)

        sf = ttk.LabelFrame(left, text="Розв'язання", padding=6)
        sf.pack(fill="x", pady=6)
        for text, mode in [
            ("Жадібний алгоритм",    "greedy"),
            ("Мурашиний алгоритм", "aco"),
            ("Обидва (порівняння)",  "both"),
        ]:
            ttk.Button(sf, text=text, width=22,
                       command=lambda m=mode: self._on_solve(m)).pack(pady=2)

        self.lbl_result = ttk.Label(
            left, text="", wraplength=240,
            font=("Consolas", 9), foreground="#2c3e50",
        )
        self.lbl_result.pack(pady=4)

    def _build_right(self, right: ttk.Frame) -> None:
        self.fig, self.axes = plt.subplots(1, 2, figsize=(9, 5.5))
        self.fig.patch.set_facecolor("#ecf0f1")
        for ax in self.axes:
            ax.set_visible(False)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _entry(self, parent, label: str, default: str, row: int) -> tk.StringVar:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        var = tk.StringVar(value=default)
        ttk.Entry(parent, textvariable=var, width=10).grid(row=row, column=1, padx=4)
        return var

    def get_aco_params(self) -> Optional[AcoParams]:
        """Зчитує параметри ACO з полів інтерфейсу."""
        try:
            return AcoParams(
                m=int(self.var_m.get()),
                n_iter=int(self.var_n_iter.get()),
                alpha=float(self.var_alpha.get()),
                beta=float(self.var_beta.get()),
                rho=float(self.var_rho.get()),
            )
        except ValueError:
            messagebox.showerror("Помилка", "Перевірте параметри ACO (m, N, α, β, ρ)")
            return None

    def _add_row(self) -> None:
        dlg = tk.Toplevel(self)
        dlg.title("Нова точка")
        dlg.resizable(False, False)
        dlg.grab_set()
        vars_ = []
        for i, (lbl, val) in enumerate([("X, мм:", "0"), ("Y, мм:", "0"), ("q, од.:", "10")]):
            ttk.Label(dlg, text=lbl).grid(row=i, column=0, padx=8, pady=4, sticky="w")
            v = tk.StringVar(value=val)
            ttk.Entry(dlg, textvariable=v, width=10).grid(row=i, column=1, padx=8, pady=4)
            vars_.append(v)

        def ok():
            try:
                x, y, q = float(vars_[0].get()), float(vars_[1].get()), float(vars_[2].get())
                n = len(self.tree.get_children()) + 1
                self.tree.insert("", "end", values=(n, x, y, q))
                dlg.destroy()
            except ValueError:
                messagebox.showerror("Помилка", "Введіть числові значення", parent=dlg)

        ttk.Button(dlg, text="OK", command=ok).grid(row=3, column=0, columnspan=2, pady=8)

    def _del_row(self) -> None:
        for item in self.tree.selection():
            self.tree.delete(item)
        self._renumber()

    def clear_rows(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _renumber(self) -> None:
        for i, item in enumerate(self.tree.get_children(), 1):
            vals = list(self.tree.item(item, "values"))
            vals[0] = i
            self.tree.item(item, values=vals)

    def get_task(self) -> Optional[ProblemInstance]:
        try:
            Q   = float(self.var_Q.get())
            tau = float(self.var_tau.get())
            v   = float(self.var_v.get())
        except ValueError:
            messagebox.showerror("Помилка", "Перевірте глобальні параметри (Q, τ, v)")
            return None

        points = []
        for item in self.tree.get_children():
            vals = self.tree.item(item, "values")
            try:
                points.append(SolderPoint(float(vals[1]), float(vals[2]), float(vals[3])))
            except (IndexError, ValueError):
                messagebox.showerror("Помилка", "Некоректні дані у таблиці точок")
                return None

        if not points:
            messagebox.showwarning("Попередження", "Додайте хоча б одну точку пайки")
            return None
        for p in points:
            if p.q > Q:
                messagebox.showerror(
                    "Помилка", f"Витрата ({p.q}) перевищує місткість подавача Q={Q}"
                )
                return None

        task = ProblemInstance(points=points, Q=Q, tau=tau, v=v)
        task.build_dist()
        return task

    def load_points(self, points: list, Q: float, tau: float, v: float) -> None:
        self.var_Q.set(str(Q))
        self.var_tau.set(str(tau))
        self.var_v.set(str(v))
        self.clear_rows()
        for i, p in enumerate(points, 1):
            self.tree.insert("", "end", values=(i, p.x, p.y, p.q))

    def show_result(
        self,
        greedy: Optional[Solution],
        aco: Optional[Solution],
    ) -> None:
        lines = []
        if greedy:
            lines.append(f"Жадібний:  {greedy.total_time:.3f} с  ({greedy.algo_time * 1000:.2f} мс)")
            for i, r in enumerate(greedy.routes, 1):
                lines.append(f"  M{i}: R→{'→'.join(map(str, r))}→R")
        if aco:
            lines.append(f"ACO:       {aco.total_time:.3f} с  ({aco.algo_time * 1000:.2f} мс)")
            for i, r in enumerate(aco.routes, 1):
                lines.append(f"  M{i}: R→{'→'.join(map(str, r))}→R")
        if greedy and aco and greedy.total_time > 0:
            delta = (greedy.total_time - aco.total_time) / greedy.total_time * 100
            lines.append(f"Покращення ACO (δ): {delta:.2f}%")
        self.lbl_result.config(text="\n".join(lines))

    def draw_solutions(
        self,
        task: ProblemInstance,
        greedy: Optional[Solution],
        aco: Optional[Solution],
    ) -> None:
        for ax in self.axes:
            ax.set_visible(False)
        if greedy and aco:
            self.axes[0].set_visible(True)
            self.axes[1].set_visible(True)
            draw_route(self.axes[0], task, greedy, f"Жадібний  [{greedy.total_time:.2f} с]")
            draw_route(self.axes[1], task, aco,     f"Мурашиний (ACO)  [{aco.total_time:.2f} с]")
        elif greedy:
            self.axes[0].set_visible(True)
            draw_route(self.axes[0], task, greedy, f"Жадібний  [{greedy.total_time:.2f} с]")
        elif aco:
            self.axes[0].set_visible(True)
            draw_route(self.axes[0], task, aco, f"Мурашиний (ACO)  [{aco.total_time:.2f} с]")
        self.fig.tight_layout()
        self.canvas.draw()

    def _import_json(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("All", "*.*")])
        if not path:
            return
        import json
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            task = ProblemInstance.from_dict(d)
            self.load_points(task.points, task.Q, task.tau, task.v)
        except Exception as e:
            messagebox.showerror("Помилка імпорту", str(e))

    def _export_json(self) -> None:
        task = self.get_task()
        if task is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON", "*.json")]
        )
        if not path:
            return
        import json
        with open(path, "w", encoding="utf-8") as f:
            json.dump(task.to_dict(), f, ensure_ascii=False, indent=2)
        messagebox.showinfo("Готово", f"Збережено: {path}")
