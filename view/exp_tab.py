"""
view/exp_tab.py
Вкладка «Експерименти» з трьома серіями:
  Серія 1 (розд. 3.3.4) — вплив розмірності n на час та точність
  Серія 2 (розд. 3.3.2) — визначення параметра умови завершення K
  Серія 3 (розд. 3.3.3) — дослідження впливу α та β
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Optional, Tuple, Callable

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Серія 1: (n, avg_greedy_ms, avg_aco_ms, delta_avg, delta_max)
ExpRow1 = Tuple[int, float, float, Optional[float], Optional[float]]
# Серія 2: (iter_no, avg_best_Z)
ExpRow2 = Tuple[int, float]
# Серія 3: (alpha, beta, avg_delta)
ExpRow3 = Tuple[float, float, float]


class ExpTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, on_run: Callable[[dict], None]):
        super().__init__(parent)
        self._on_run = on_run
        self._results1: List[ExpRow1] = []
        self._results2: List[ExpRow2] = []
        self._results3: List[ExpRow3] = []
        self._build()

    # ── Побудова інтерфейсу ─────────────────────────────────────

    def _build(self) -> None:
        # Ліва панель — параметри
        left = ttk.LabelFrame(self, text="Параметри дослідження", padding=8)
        left.pack(side="left", fill="y", padx=(6, 4), pady=6)

        # Права панель — notebook з трьома вкладками результатів
        right = ttk.Frame(self)
        right.pack(side="right", fill="both", expand=True, padx=(4, 6), pady=6)

        self._build_left(left)
        self._build_right(right)

    def _build_left(self, left: ttk.LabelFrame) -> None:
        # ── Фіксовані параметри задач ──
        fp = ttk.LabelFrame(left, text="Параметри задачі (фіксовані)", padding=6)
        fp.pack(fill="x", pady=(0, 4))
        self.exp_Q   = self._entry(fp, "Q, од.:",   "100", 0)
        self.exp_tau = self._entry(fp, "τ, с:",     "10",  1)
        self.exp_v   = self._entry(fp, "v, мм/с:",  "15",  2)
        self.exp_qlo = self._entry(fp, "q мін:",    "10",  3)
        self.exp_qhi = self._entry(fp, "q макс:",   "35",  4)

        # ── Базові параметри ACO ──
        ap = ttk.LabelFrame(left, text="Базові параметри ACO", padding=6)
        ap.pack(fill="x", pady=(0, 4))
        self.exp_m      = self._entry(ap, "Мурах m:",        "20",  0)
        self.exp_n_iter = self._entry(ap, "Ітерації N_max:", "100", 1)
        self.exp_alpha  = self._entry(ap, "α (базове):",     "1",   2)
        self.exp_beta   = self._entry(ap, "β (базове):",     "2",   3)
        self.exp_rho    = self._entry(ap, "ρ:",              "0.5", 4)
        self.exp_k      = self._entry(ap, "K (базове):",     "50",  5)

        # ── Серія 1: вплив розмірності n ──
        s1 = ttk.LabelFrame(left, text="Серія 1 (розд. 3.3.4): вплив n", padding=6)
        s1.pack(fill="x", pady=(0, 4))
        self.exp_n_from  = self._entry(s1, "n від:", "5",  0)
        self.exp_n_to    = self._entry(s1, "n до:",  "20", 1)
        self.exp_n_step  = self._entry(s1, "крок:",  "1",  2)
        self.exp_n_count = self._entry(s1, "задач:", "30", 3)
        self.exp_n_fixed = self._entry(s1, "n фікс (С2,С3):", "15", 4)

        # ── Серія 2: визначення K ──
        s2 = ttk.LabelFrame(left, text="Серія 2 (розд. 3.3.2): визначення K", padding=6)
        s2.pack(fill="x", pady=(0, 4))
        self.exp_k_tasks    = self._entry(s2, "задач:",       "20",  0)
        self.exp_k_itermax  = self._entry(s2, "I_max:",       "500", 1)

        # ── Серія 3: вплив α та β ──
        s3 = ttk.LabelFrame(left, text="Серія 3 (розд. 3.3.3): вплив α, β", padding=6)
        s3.pack(fill="x", pady=(0, 4))
        self.exp_ab_tasks = self._entry(s3, "задач:", "20", 0)
        ttk.Label(s3, text="α: 1,2,3  β: 1,2,3 (фікс)", font=("Consolas", 8),
                  foreground="#555").grid(row=1, column=0, columnspan=2, sticky="w", pady=2)

        # ── Кнопки та прогрес ──
        bf = ttk.Frame(left)
        bf.pack(fill="x", pady=4)
        ttk.Button(bf, text="▶ Запустити всі серії", width=24,
                   command=self._fire_all).pack(pady=2)
        ttk.Button(bf, text="Серія 1 окремо", width=24,
                   command=lambda: self._fire(series=1)).pack(pady=1)
        ttk.Button(bf, text="Серія 2 окремо", width=24,
                   command=lambda: self._fire(series=2)).pack(pady=1)
        ttk.Button(bf, text="Серія 3 окремо", width=24,
                   command=lambda: self._fire(series=3)).pack(pady=1)
        ttk.Button(bf, text="Експорт CSV", width=24,
                   command=self._export_csv).pack(pady=4)

        self.prog_var = tk.DoubleVar()
        ttk.Progressbar(left, variable=self.prog_var, maximum=100,
                        length=220).pack(pady=2)
        self.lbl_prog = ttk.Label(left, text="", font=("Consolas", 8))
        self.lbl_prog.pack()

    def _build_right(self, right: ttk.Frame) -> None:
        nb = ttk.Notebook(right)
        nb.pack(fill="both", expand=True)

        # ── Вкладка Серія 1 ──
        tab1 = ttk.Frame(nb)
        nb.add(tab1, text="  Серія 1: розмірність n  ")
        cols1 = ("n", "Жад, мс", "ACO, мс", "δ̄, %", "δ_max, %")
        self.tree1 = self._make_tree(tab1, cols1, widths=[60,90,90,80,80])
        self.fig1, (self.ax1a, self.ax1b) = plt.subplots(1, 2, figsize=(9, 3.8))
        self.fig1.patch.set_facecolor("#ecf0f1")
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=tab1)
        self.canvas1.get_tk_widget().pack(fill="both", expand=True)

        # ── Вкладка Серія 2 ──
        tab2 = ttk.Frame(nb)
        nb.add(tab2, text="  Серія 2: умова завершення K  ")
        cols2 = ("Ітерація", "Середній T*, с")
        self.tree2 = self._make_tree(tab2, cols2, widths=[100, 130])
        self.fig2, self.ax2 = plt.subplots(1, 1, figsize=(9, 3.8))
        self.fig2.patch.set_facecolor("#ecf0f1")
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=tab2)
        self.canvas2.get_tk_widget().pack(fill="both", expand=True)

        # ── Вкладка Серія 3 ──
        tab3 = ttk.Frame(nb)
        nb.add(tab3, text="  Серія 3: вплив α та β  ")
        cols3 = ("α", "β", "δ̄, %")
        self.tree3 = self._make_tree(tab3, cols3, widths=[80, 80, 100])
        self.fig3, self.ax3 = plt.subplots(1, 1, figsize=(9, 3.8))
        self.fig3.patch.set_facecolor("#ecf0f1")
        self.canvas3 = FigureCanvasTkAgg(self.fig3, master=tab3)
        self.canvas3.get_tk_widget().pack(fill="both", expand=True)

    def _make_tree(self, parent, cols, widths) -> ttk.Treeview:
        tree = ttk.Treeview(parent, columns=cols, show="headings", height=8)
        for c, w in zip(cols, widths):
            tree.heading(c, text=c)
            tree.column(c, width=w, anchor="center")
        sb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="top", fill="x")
        sb.pack(side="right", fill="y")
        return tree

    def _entry(self, parent, label: str, default: str, row: int) -> tk.StringVar:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        var = tk.StringVar(value=default)
        ttk.Entry(parent, textvariable=var, width=10).grid(row=row, column=1, padx=4)
        return var

    # ── Збір параметрів ─────────────────────────────────────────

    def _collect_params(self) -> Optional[dict]:
        try:
            return {
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
                "aco_k":      int(self.exp_k.get()),
                # Серія 1
                "n_from":  int(self.exp_n_from.get()),
                "n_to":    int(self.exp_n_to.get()),
                "n_step":  int(self.exp_n_step.get()),
                "count":   int(self.exp_n_count.get()),
                "n_fixed": int(self.exp_n_fixed.get()),
                # Серія 2
                "k_tasks":   int(self.exp_k_tasks.get()),
                "k_itermax": int(self.exp_k_itermax.get()),
                # Серія 3
                "ab_tasks": int(self.exp_ab_tasks.get()),
            }
        except ValueError:
            messagebox.showerror("Помилка", "Перевірте параметри дослідження")
            return None

    def _fire_all(self) -> None:
        p = self._collect_params()
        if p:
            p["series"] = "all"
            self._reset_all()
            self._on_run(p)

    def _fire(self, series: int) -> None:
        p = self._collect_params()
        if p:
            p["series"] = series
            self._reset_series(series)
            self._on_run(p)

    def _reset_all(self) -> None:
        for s in (1, 2, 3):
            self._reset_series(s)

    def _reset_series(self, s: int) -> None:
        if s == 1:
            self._results1 = []
            for item in self.tree1.get_children():
                self.tree1.delete(item)
        elif s == 2:
            self._results2 = []
            for item in self.tree2.get_children():
                self.tree2.delete(item)
        elif s == 3:
            self._results3 = []
            for item in self.tree3.get_children():
                self.tree3.delete(item)
        self.prog_var.set(0)

    # ── Методи оновлення UI (викликаються з контролера через after()) ──

    def set_progress(self, pct: float, text: str) -> None:
        self.prog_var.set(pct)
        self.lbl_prog.config(text=text)

    # Серія 1
    def add_row1(self, row: ExpRow1) -> None:
        self._results1.append(row)
        n, tg, ta, avg_d, max_d = row
        self.tree1.insert("", "end", values=(
            n,
            f"{tg:.3f}",
            f"{ta:.3f}",
            f"{avg_d:.2f}" if avg_d is not None else "—",
            f"{max_d:.2f}" if max_d is not None else "—",
        ))

    def draw_charts1(self, results: List[ExpRow1]) -> None:
        ns  = [r[0] for r in results]
        tg  = [r[1] for r in results]
        ta  = [r[2] for r in results]
        dev = [r[3] for r in results]

        self.ax1a.clear()
        self.ax1a.set_title("Час виконання алгоритмів", fontsize=10, fontweight="bold")
        self.ax1a.plot(ns, tg, "o-", color="#e74c3c", label="Жадібний")
        self.ax1a.plot(ns, ta, "s-", color="#2980b9", label="Мурашиний (ACO)")
        self.ax1a.set_xlabel("n (точок пайки)")
        self.ax1a.set_ylabel("Час, мс")
        self.ax1a.legend()
        self.ax1a.grid(True, linestyle="--", alpha=0.4)

        self.ax1b.clear()
        self.ax1b.set_title("Покращення ACO відносно жадібного (δ̄)", fontsize=10, fontweight="bold")
        d_ns = [ns[i] for i, v in enumerate(dev) if v is not None]
        d_dv = [v for v in dev if v is not None]
        if d_dv:
            self.ax1b.bar(d_ns, d_dv, color="#27ae60", alpha=0.8, label="δ̄, %")
        self.ax1b.axhline(10, color="#e74c3c", linestyle="--", label="10% поріг")
        self.ax1b.set_xlabel("n (точок пайки)")
        self.ax1b.set_ylabel("Покращення, %")
        self.ax1b.legend()
        self.ax1b.grid(True, linestyle="--", alpha=0.4)

        self.fig1.tight_layout()
        self.canvas1.draw()

    # Серія 2
    def add_row2(self, row: ExpRow2) -> None:
        self._results2.append(row)
        iter_no, avg_z = row
        self.tree2.insert("", "end", values=(iter_no, f"{avg_z:.3f}"))

    def draw_charts2(self, results: List[ExpRow2]) -> None:
        iters = [r[0] for r in results]
        vals  = [r[1] for r in results]

        self.ax2.clear()
        self.ax2.set_title(
            "Динаміка рекордного значення T* (Серія 2: визначення K)",
            fontsize=10, fontweight="bold"
        )
        self.ax2.plot(iters, vals, "-", color="#8e44ad", linewidth=1.5)
        self.ax2.set_xlabel("Номер ітерації")
        self.ax2.set_ylabel("Середній T*, с")
        self.ax2.grid(True, linestyle="--", alpha=0.4)
        self.fig2.tight_layout()
        self.canvas2.draw()

    # Серія 3
    def add_row3(self, row: ExpRow3) -> None:
        self._results3.append(row)
        alpha, beta, avg_d = row
        self.tree3.insert("", "end", values=(
            f"{alpha:.0f}", f"{beta:.0f}", f"{avg_d:.2f}"
        ))

    def draw_charts3(self, results: List[ExpRow3]) -> None:
        labels = [f"α={r[0]:.0f}\nβ={r[1]:.0f}" for r in results]
        deltas = [r[2] for r in results]
        colors = ["#2980b9" if d == max(deltas) else "#85c1e9" for d in deltas]

        self.ax3.clear()
        self.ax3.set_title(
            "Вплив α та β на покращення ACO (δ̄, %) (Серія 3)",
            fontsize=10, fontweight="bold"
        )
        x = range(len(labels))
        bars = self.ax3.bar(x, deltas, color=colors, alpha=0.85)
        self.ax3.set_xticks(list(x))
        self.ax3.set_xticklabels(labels, fontsize=8)
        self.ax3.set_ylabel("δ̄, %")
        self.ax3.axhline(0, color="black", linewidth=0.8)
        self.ax3.grid(True, axis="y", linestyle="--", alpha=0.4)
        # підписи над стовпцями
        for bar, val in zip(bars, deltas):
            self.ax3.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.1,
                f"{val:.1f}%",
                ha="center", va="bottom", fontsize=8
            )
        self.fig3.tight_layout()
        self.canvas3.draw()

    # ── Сумісність зі старим контролером ────────────────────────
    # (залишено для зворотної сумісності)
    def add_row(self, row) -> None:
        self.add_row1(row)

    def set_results(self, results) -> None:
        self._results1 = results

    def draw_charts(self, results) -> None:
        self.draw_charts1(results)

    # ── Експорт CSV ─────────────────────────────────────────────

    def _export_csv(self) -> None:
        if not self._results1 and not self._results2 and not self._results3:
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
            if self._results1:
                w.writerow(["=== Серія 1: вплив розмірності n ==="])
                w.writerow(["n", "Жадібний, мс", "ACO, мс", "δ̄, %", "δ_max, %"])
                for r in self._results1:
                    w.writerow([r[0], f"{r[1]:.4f}", f"{r[2]:.4f}",
                                f"{r[3]:.3f}" if r[3] else "—",
                                f"{r[4]:.3f}" if r[4] else "—"])
                w.writerow([])
            if self._results2:
                w.writerow(["=== Серія 2: динаміка рекорду T* ==="])
                w.writerow(["Ітерація", "Середній T*, с"])
                for r in self._results2:
                    w.writerow([r[0], f"{r[1]:.4f}"])
                w.writerow([])
            if self._results3:
                w.writerow(["=== Серія 3: вплив α та β ==="])
                w.writerow(["α", "β", "δ̄, %"])
                for r in self._results3:
                    w.writerow([f"{r[0]:.0f}", f"{r[1]:.0f}", f"{r[2]:.3f}"])
        messagebox.showinfo("Готово", f"Збережено: {path}")
