from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PathLikeValue = str | Path


@dataclass(frozen=True, slots=True)
class Open:
    """
    Открыть файл через системное приложение по умолчанию
    или через явно заданную программу.
    """

    path: PathLikeValue
    app: PathLikeValue | None = None


@dataclass(frozen=True, slots=True)
class Text:
    """
    Показать текст в отдельном окне приложения.
    """

    text: str
    title: str | None = None


@dataclass(frozen=True, slots=True)
class Link:
    """
    Открыть ссылку в браузере по умолчанию.
    """

    url: str


@dataclass(frozen=True, slots=True)
class Copy:
    """
    Скопировать текст в буфер обмена.

    Поле `notification` позволит показать человеку короткое подтверждение.
    """

    text: str
    notification: str | None = None


@dataclass(frozen=True, slots=True)
class Notify:
    """
    Показать нативное уведомление.
    """

    title: str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class Folder:
    """
    Открыть папку.
    """

    path: PathLikeValue


ActionResult = Open | Text | Link | Copy | Notify | Folder | None