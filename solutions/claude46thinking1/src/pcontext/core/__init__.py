"""
pcontext.core — Ядро приложения PContext.

Содержит:
  • constants  — все константы (пути, порты, расширения файлов, ...)
  • config     — управление настройками приложения           (Этап 4)
  • script_loader   — загрузка и парсинг .py-скриптов        (Этап 4)
  • script_registry — глобальный реестр скриптов              (Этап 4)
  • script_executor — запуск скриптов с таймаутами            (Этап 8)
  • service_manager — жизненный цикл сервисов                 (Этап 9)
  • action_handler  — обработка Open, Copy, Notify, ...       (Этап 8)
  • param_store     — хранение значений параметров (Param)    (Этап 4)
  • log_store       — SQLite-хранилище логов запуска          (Этап 11)
  • venv_manager    — создание venv и установка зависимостей  (Этап 5)

Экспортируемые функции:
  • ensure_directories() — создание всех директорий приложения
"""

from __future__ import annotations

from pcontext.core.constants import (
    CACHE_DIR,
    CONFIG_DIR,
    LOGS_DIR,
    PCONTEXT_HOME,
    SCRIPTS_DIR,
    VENV_DIR,
)

# Контролируем, что экспортируется при «from pcontext.core import *»
__all__: list[str] = ["ensure_directories"]


def ensure_directories() -> None:
    """
    Создаёт все необходимые директории приложения PContext.

    Безопасно вызывать многократно: если директории уже существуют,
    ничего не происходит (параметр exist_ok=True).

    Создаваемая структура на диске::

        ~/.pcontext/
        ├── scripts/     ← пользовательские скрипты (подпапки = группы)
        ├── venv/        ← виртуальное окружение для pip-зависимостей
        ├── config/      ← settings.json, params.json, scripts_cache.json
        ├── logs/        ← runs.db (SQLite с историей запусков)
        └── cache/       ← временные файлы (результаты скриптов и пр.)
    """
    # Собираем все директории в список для удобства итерации
    directories = [
        PCONTEXT_HOME,   # ~/.pcontext/
        SCRIPTS_DIR,     # ~/.pcontext/scripts/
        VENV_DIR,        # ~/.pcontext/venv/
        CONFIG_DIR,      # ~/.pcontext/config/
        LOGS_DIR,        # ~/.pcontext/logs/
        CACHE_DIR,       # ~/.pcontext/cache/
    ]

    for directory in directories:
        # parents=True  → создаёт все промежуточные папки, если их нет
        # exist_ok=True → не выбрасывает исключение, если папка уже есть
        directory.mkdir(parents=True, exist_ok=True)