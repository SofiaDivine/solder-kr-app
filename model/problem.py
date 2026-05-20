"""
model/problem.py
Структури даних задачі: точка пайки, умова задачі, розв'язок.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SolderPoint:
    """Точка пайки з координатами та витратою припою."""
    x: float
    y: float
    q: float  # витрата припою (одиниць)


@dataclass
class ProblemInstance:
    """
    Повна умова задачі маршрутизації паяльної головки.

    Атрибути:
        points : список точок пайки
        Q      : місткість подавача припою (одиниці)
        tau    : час одного повного заправлення (секунди)
        v      : швидкість переміщення головки (мм/с)
        dist   : матриця часів переміщення (індекс 0 = база R)
    """
    points: List[SolderPoint]
    Q: float
    tau: float
    v: float
    dist: List[List[float]] = field(default_factory=list)

    # ── побудова матриці відстаней ──────────────────────────────

    def build_dist(self) -> None:
        """Обчислює матрицю евклідових часів переміщення.
        Індекс 0 відповідає базі R(0, 0).
        """
        n = len(self.points)
        coords = [(0.0, 0.0)] + [(p.x, p.y) for p in self.points]
        size = n + 1
        self.dist = [[0.0] * size for _ in range(size)]
        for i in range(size):
            for j in range(size):
                dx = coords[i][0] - coords[j][0]
                dy = coords[i][1] - coords[j][1]
                self.dist[i][j] = math.sqrt(dx * dx + dy * dy) / self.v

    # ── серіалізація ────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "Q": self.Q,
            "tau": self.tau,
            "v": self.v,
            "points": [{"x": p.x, "y": p.y, "q": p.q} for p in self.points],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ProblemInstance":
        pts = [SolderPoint(**p) for p in d["points"]]
        inst = cls(points=pts, Q=d["Q"], tau=d["tau"], v=d["v"])
        inst.build_dist()
        return inst


@dataclass
class Solution:
    """Розв'язок задачі: список підмаршрутів і загальний час."""
    routes: List[List[int]]   # кожен підмаршрут — індекси точок (1-based)
    total_time: float          # загальний час виконання маршруту (с)
    algo_time: float = 0.0     # час роботи алгоритму (с)
    algo_name: str = ""        # назва алгоритму
