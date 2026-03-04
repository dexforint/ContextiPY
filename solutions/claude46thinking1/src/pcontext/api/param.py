"""
pcontext.api.param — Параметр скрипта, настраиваемый пользователем.

Param позволяет объявить параметр скрипта, значение которого можно
изменять через GUI (tray → Скрипты → настройка), не редактируя код.

Пример использования:

    from enum import Enum
    from pcontext import Param

    class ModelName(str, Enum):
        small = "yolov8n.pt"
        large = "yolov8s.pt"

    @oneshot_script(title="Детекция")
    def detect(
        image: str = Image(),
        model: ModelName = Param("yolov8n.pt"),
        threshold: float = Param(0.5, ge=0.0, le=1.0),
    ):
        ...
"""

from __future__ import annotations

from typing import Any


class Param:
    """
    Описание настраиваемого параметра скрипта.

    Атрибуты:
        default — значение по умолчанию (обязательно)
        ge      — минимально допустимое значение (>=), для числовых типов
        le      — максимально допустимое значение (<=), для числовых типов
        description — человекочитаемое описание параметра

    При отображении в GUI тип параметра определяется автоматически
    по аннотации типа в функции-скрипте:
        • str        → текстовое поле
        • int        → числовое поле (целые)
        • float      → числовое поле (дробные)
        • bool       → чекбокс
        • Enum       → выпадающий список
    """

    def __init__(
        self,
        default: Any,
        *,
        ge: int | float | None = None,
        le: int | float | None = None,
        description: str = "",
    ) -> None:
        self.default: Any = default
        self.ge: int | float | None = ge
        self.le: int | float | None = le
        self.description: str = description

    def __repr__(self) -> str:
        """Строковое представление для отладки."""
        parts = [f"default={self.default!r}"]
        if self.ge is not None:
            parts.append(f"ge={self.ge}")
        if self.le is not None:
            parts.append(f"le={self.le}")
        if self.description:
            parts.append(f"description={self.description!r}")
        return f"Param({', '.join(parts)})"