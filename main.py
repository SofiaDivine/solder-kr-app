"""
main.py — точка входу застосунку «Маршрут пайки».

Запуск:
    python main.py
"""

import sys
import os

# Дозволяємо імпорт пакетів (model, view, controller, utils)
# при запуску безпосередньо з кореня проєкту
sys.path.insert(0, os.path.dirname(__file__))

from controller.app_controller import AppController


def main() -> None:
    app = AppController()
    app.mainloop()


if __name__ == "__main__":
    main()
