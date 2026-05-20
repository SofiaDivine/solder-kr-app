"""
utils/generator.py
Генератор випадкових екземплярів задачі для тестування та експериментів.
"""

from __future__ import annotations
import random
from typing import Optional

from model.problem import ProblemInstance, SolderPoint


def generate_task(
    n: int,
    Q: float = 100.0,
    tau: float = 10.0,
    v: float = 15.0,
    q_min: float = 10.0,
    q_max: float = 35.0,
    field_size: float = 100.0,
    seed: Optional[int] = None,
) -> ProblemInstance:
    """
    Генерує випадковий екземпляр задачі.

    Параметри:
        n          — кількість точок пайки
        Q          — місткість подавача
        tau        — час дозаправки (с)
        v          — швидкість головки (мм/с)
        q_min      — мінімальна витрата припою в точці
        q_max      — максимальна витрата (буде обрізана до Q)
        field_size — розмір поля (мм), точки у квадраті [0, field_size]²
        seed       — зерно генератора (для відтворюваності)

    Повертає: ProblemInstance з побудованою матрицею відстаней
    """
    rng = random.Random(seed)
    points = [
        SolderPoint(
            x=round(rng.uniform(0, field_size), 2),
            y=round(rng.uniform(0, field_size), 2),
            q=round(rng.uniform(q_min, min(q_max, Q)), 2),
        )
        for _ in range(n)
    ]
    task = ProblemInstance(points=points, Q=Q, tau=tau, v=v)
    task.build_dist()
    return task
