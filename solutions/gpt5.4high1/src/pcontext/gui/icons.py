from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QStyle

from pcontext.config import PContextPaths


def load_application_icon(paths: PContextPaths, application: QApplication) -> QIcon:
    """
    Загружает иконку приложения из пользовательской папки PContext.

    Приоритет такой:
    1. ~/.pcontext/icons/pcontext.ico
    2. ~/.pcontext/icons/pcontext.png
    3. ~/.pcontext/icons/pcontext.svg
    4. ~/.pcontext/pcontext.ico
    5. ~/.pcontext/pcontext.png
    6. ~/.pcontext/pcontext.svg

    Если пользовательская иконка не найдена, используется стандартная системная.
    """
    for candidate in _iter_icon_candidates(paths):
        if not candidate.is_file():
            continue

        icon = QIcon(str(candidate))
        if not icon.isNull():
            return icon

    return application.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)


def _iter_icon_candidates(paths: PContextPaths) -> tuple[Path, ...]:
    """
    Возвращает список путей, где мы ищем иконку приложения.
    """
    names = (
        "pcontext.ico",
        "pcontext.png",
        "pcontext.svg",
    )

    icon_paths = [paths.icons / name for name in names]
    home_paths = [paths.home / name for name in names]

    return tuple(icon_paths + home_paths)
