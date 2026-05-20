"""
view/route_canvas.py
Допоміжні функції для відображення маршрутів на matplotlib-полотні.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from model.problem import ProblemInstance, Solution

COLORS = [
    "#e74c3c", "#2980b9", "#27ae60", "#f39c12",
    "#8e44ad", "#16a085", "#c0392b", "#2c3e50",
]


def draw_route(
    ax: "Axes",
    task: "ProblemInstance",
    sol: "Solution",
    title: str,
) -> None:
    """
    Відображає маршрут на осях matplotlib.

    Параметри:
        ax    — осі matplotlib
        task  — умова задачі (для координат точок)
        sol   — розв'язок для відображення
        title — заголовок графіка
    """
    ax.clear()
    ax.set_facecolor("#f8f9fa")
    ax.set_title(title, fontsize=11, fontweight="bold", pad=8)
    ax.set_ylabel("Y, мм", fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.4)

    # База R
    ax.plot(0, 0, "ks", markersize=12, zorder=5, label="База R")
    ax.annotate(
        "R", (0, 0),
        textcoords="offset points", xytext=(6, 6),
        fontsize=9, fontweight="bold",
    )

    # Підмаршрути
    for idx, (route, color) in enumerate(zip(sol.routes, COLORS)):
        path = [0] + route + [0]
        xs = [0 if p == 0 else task.points[p - 1].x for p in path]
        ys = [0 if p == 0 else task.points[p - 1].y for p in path]
        ax.plot(
            xs, ys, "-o",
            color=color, linewidth=2, markersize=7,
            label=f"Маршрут {idx + 1}: {[str(p) for p in route]}",
        )
        for p in route:
            px, py = task.points[p - 1].x, task.points[p - 1].y
            ax.annotate(
                f"P{p}\n(q={task.points[p - 1].q:.0f})",
                (px, py),
                textcoords="offset points", xytext=(6, 4),
                fontsize=7.5, color=color,
            )

    ax.legend(fontsize=8, loc="upper left", framealpha=0.85)
    t_str = (
        f"Загальний час: {sol.total_time:.2f} с"
        f"  |  Алгоритм: {sol.algo_time * 1000:.2f} мс"
    )
    ax.set_xlabel(f"X, мм  |  {t_str}", fontsize=8.5)
