"""
view/exp_tab.py
Вкладка «Експерименти»: серійні запуски, таблиця результатів,
графіки часу та покращення ACO відносно жадібного.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Optional, Tuple, Callable

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# (n, avg_greedy_ms, avg_aco_ms, delta_avg, delta_max)
ExpRow = Tuple[int, float, float, Optional[float], Optional[float]]


class ExpTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, on_run: Callable[[dict], None]):
        super().__init__(parent)
        self._on_run = on_run
        self._results: List[ExpRow] = []
        self._build()

    def _build(self) -> None:
        left = ttk.LabelFrame(self, text="Параметри дослідження", padding=10)
        left.pack(side="left", fill="y", padx=(6, 4), pady=6)
        self._build_left(left)

        right = ttk.Frame(self)
        right.pack(side="right", fill="both", expand=True, padx=(4, 6), pady=6)
        self._build_right(right)

    def _build_left(self, left: ttk.LabelFrame) -> None:
        s1 = ttk.LabelFrame(left, text="Серія 1: вплив розмірності n", padding=6)
        s1.pack(fill="x", pady=4)
        self.exp_n_from  = self._entry(s1, "n від:",  "5",  0)
        self.exp_n_to    = self._entry(s1, "n до:",   "12", 1)
        self.exp_n_step  = self._entry(s1, "крок:",   "1",  2)
        self.exp_n_count = self._entry(s1, "задач:",  "30", 3)

        fp = ttk.LabelFrame(left, text="Фіксовані параметри задач", padding=6)
        fp.pack(fill="x", pady=4)
        self.exp_Q   = self._entry(fp, "Q, од.:",  "100", 0)
        self.exp_tau = self._entry(fp, "τ, с:",    "10",  1)
        self.exp_v   = self._entry(fp, "v, мм/с:", "15",  2)
        self.exp_qlo = self._entry(fp, "q мін:",   "10",  3)
        self.exp_qhi = self._entry(fp, "q макс:",  "35",  4)

        ap = ttk.LabelFrame(left, text="Параметри ACO", padding=6)
        ap.pack(fill="x", pady=4)
        self.exp_m      = self._entry(ap, "Мурах m:",     "20",  0)
        self.exp_n_iter = self._entry(ap, "Ітерації N:",  "100", 1)
        self.exp_alpha  = self._entry(ap, "α:",           "1",   2)
        self.exp_beta   = self._entry(ap, "β:",           "2",   3)
        self.exp_rho    = self._entry(ap, "ρ:",           "0.1", 4)

        ttk.Button(left, text="Запустити дослідження", width=26,
                   command=self._fire_run).pack(pady=6)
        ttk.Button(left, text="Експорт у CSV", width=26,
                   command=self._export_csv).pack(pady=2)

        self.prog_var = tk.DoubleVar()
        ttk.Progressbar(left, variable=self.prog_var, maximum=100, length=220).pack(pady=4)
        self.lbl_prog = ttk.Label(left, text="", font=("Consolas", 8))
        self.lbl_prog.pack()

    def _build_right(self, right: ttk.Frame) -> None:
        cols = ("n", "Жад, мс", "ACO, мс", "δ̄, %", "δ_max, %")
        self.res_tree = ttk.Treeview(right, columns=cols, show="headings", height=10)
        for c in cols:
            self.res_tree.heading(c, text=c)
            self.res_tree.column(c, width=90, anchor="center")
        sb = ttk.Scrollbar(right, orient="vertical", command=self.res_tree.yview)
        self.res_tree.configure(yscrollcommand=sb.set)
        self.res_tree.pack(side="top", fill="x", pady=(0, 4))
        sb.pack(side="right", fill="y")

        self.fig2, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(9, 4))
        self.fig2.patch.set_facecolor("#ecf0f1")
        self.canvas = FigureCanvasTkAgg(self.fig2, master=right)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _entry(self, parent, label: str, default: str, row: int) -> tk.StringVar:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        var = tk.StringVar(value=default)
        ttk.Entry(parent, textvariable=var, width=10).grid(row=row, column=1, padx=4)
        return var

    def _fire_run(self) -> None:
        try:
            params = {
                "n_from":  int(self.exp_n_from.get()),
                "n_to":    int(self.exp_n_to.get()),
                "n_step":  int(self.exp_n_step.get()),
                "count":   int(self.exp_n_count.get()),
                "Q":       float(self.exp_Q.get()),
                "tau":     float(self.exp_tau.get()),
                "v":       float(self.exp_v.get()),
                "q_lo":    float(self.exp_qlo.get()),
                "q_hi":    float(self.exp_qhi.get()),
                "aco_m":      int(self.exp_m.get()),
                "aco_n_iter": int(self.exp_n_iter.get()),
                "aco_alpha":  float(self.exp_alpha.get()),
                "aco_beta":   float(self.exp_beta.get()),
                "aco_rho":    float(self.exp_rho.get()),
            }
        except ValueError:
            messagebox.showerror("Помилка", "Перевірте параметри дослідження")
            return
        self._results = []
        for item in self.res_tree.get_children():
            self.res_tree.delete(item)
        self.prog_var.set(0)
        self._on_run(params)

    def add_row(self, row: ExpRow) -> None:
        n, tg, ta, avg_d, max_d = row
        self.res_tree.insert("", "end", values=(
            n,
            f"{tg:.3f}",
            f"{ta:.3f}",
            f"{avg_d:.2f}" if avg_d is not None else "—",
            f"{max_d:.2f}" if max_d is not None else "—",
        ))

    def set_progress(self, pct: float, text: str) -> None:
        self.prog_var.set(pct)
        self.lbl_prog.config(text=text)

    def draw_charts(self, results: List[ExpRow]) -> None:
        ns  = [r[0] for r in results]
        tg  = [r[1] for r in results]
        ta  = [r[2] for r in results]
        dev = [r[3] for r in results]

        self.ax1.clear()
        self.ax1.set_title("Час виконання алгоритмів", fontsize=10, fontweight="bold")
        self.ax1.plot(ns, tg, "o-", color="#e74c3c", label="Жадібний")
        self.ax1.plot(ns, ta, "s-", color="#2980b9", label="Мурашиний (ACO)")
        self.ax1.set_xlabel("n (точок пайки)")
        self.ax1.set_ylabel("Час, мс")
        self.ax1.legend()
        self.ax1.grid(True, linestyle="--", alpha=0.4)

        self.ax2.clear()
        self.ax2.set_title("Покращення ACO відносно жадібного (δ)", fontsize=10, fontweight="bold")
        d_ns2  = [ns[i] for i, v in enumerate(dev) if v is not None]
        d_devs = [v for v in dev if v is not None]
        if d_devs:
            self.ax2.bar(d_ns2, d_devs, color="#27ae60", alpha=0.8, label="δ̄, %")
        self.ax2.axhline(10, color="#e74c3c", linestyle="--", label="10% поріг")
        self.ax2.set_xlabel("n (точок пайки)")
        self.ax2.set_ylabel("Покращення, %")
        self.ax2.legend()
        self.ax2.grid(True, linestyle="--", alpha=0.4)

        self.fig2.tight_layout()
        self.canvas.draw()

    def _export_csv(self) -> None:
        if not self._results:
            messagebox.showwarning("Попередження", "Спочатку виконайте дослідження")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")]
        )
        if not path:
            return
        import csv
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["n", "Жадібний, мс", "ACO, мс", "δ̄, %", "δ_max, %"])
            for r in self._results:
                w.writerow([
                    r[0],
                    f"{r[1]:.4f}",
                    f"{r[2]:.4f}",
                    f"{r[3]:.3f}" if r[3] else "—",
                    f"{r[4]:.3f}" if r[4] else "—",
                ])
        messagebox.showinfo("Готово", f"Збережено: {path}")

    def set_results(self, results: List[ExpRow]) -> None:
        self._results = results
