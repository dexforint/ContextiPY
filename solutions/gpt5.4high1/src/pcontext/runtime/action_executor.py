from __future__ import annotations

import os
import subprocess
import sys
import threading
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pyperclip

from pcontext.runtime.action_codec import (
    CopyAction,
    FolderActionModel,
    LinkAction,
    NoneAction,
    NotifyAction,
    OpenAction,
    SerializedAction,
    TextAction,
)


@dataclass(frozen=True, slots=True)
class ActionExecutionHooks:
    """
    Дополнительные GUI-хуки для исполнения действий.

    Они нужны, чтобы фоновый агент мог попросить GUI-поток:
    - показать окно с текстом;
    - показать уведомление через tray icon.
    """

    show_text: Callable[[str | None, str], None] | None = None
    show_notification: Callable[[str, str | None], None] | None = None


_HOOKS_LOCK = threading.RLock()
_ACTIVE_HOOKS: ActionExecutionHooks | None = None


def install_action_execution_hooks(hooks: ActionExecutionHooks | None) -> None:
    """
    Устанавливает или сбрасывает глобальные GUI-хуки.
    """
    global _ACTIVE_HOOKS

    with _HOOKS_LOCK:
        _ACTIVE_HOOKS = hooks


def clear_action_execution_hooks() -> None:
    """
    Полностью удаляет ранее установленные GUI-хуки.
    """
    install_action_execution_hooks(None)


def _get_hooks() -> ActionExecutionHooks | None:
    """
    Возвращает текущие зарегистрированные GUI-хуки.
    """
    with _HOOKS_LOCK:
        return _ACTIVE_HOOKS


def _emit_text(title: str | None, text: str) -> bool:
    """
    Пытается показать текст через GUI-хук.
    """
    hooks = _get_hooks()
    if hooks is None or hooks.show_text is None:
        return False

    hooks.show_text(title, text)
    return True


def _emit_notification(title: str, description: str | None) -> bool:
    """
    Пытается показать уведомление через GUI-хук.
    """
    hooks = _get_hooks()
    if hooks is None or hooks.show_notification is None:
        return False

    hooks.show_notification(title, description)
    return True


def _open_with_system_default(path: str) -> None:
    """
    Открывает путь стандартным способом для текущей платформы.
    """
    normalized_path = str(Path(path))

    if os.name == "nt":
        startfile = getattr(os, "startfile", None)
        if startfile is None:
            raise RuntimeError("На этой системе недоступен os.startfile.")
        startfile(normalized_path)
        return

    if sys.platform == "darwin":
        subprocess.Popen(["open", normalized_path])
        return

    subprocess.Popen(["xdg-open", normalized_path])


def execute_serialized_action(action: SerializedAction) -> str:
    """
    Исполняет действие.

    Простые действия выполняются сразу.
    GUI-действия `Text` и `Notify` пробрасываются в установленные hooks.
    """
    if isinstance(action, NoneAction):
        return "Скрипт не вернул дополнительного действия."

    if isinstance(action, OpenAction):
        if action.app is not None:
            subprocess.Popen([action.app, action.path])
            return f"Файл открыт через указанное приложение: {action.path}"

        _open_with_system_default(action.path)
        return f"Файл открыт: {action.path}"

    if isinstance(action, FolderActionModel):
        _open_with_system_default(action.path)
        return f"Папка открыта: {action.path}"

    if isinstance(action, LinkAction):
        opened = webbrowser.open(action.url)
        if not opened:
            raise RuntimeError(f"Не удалось открыть ссылку: {action.url}")
        return f"Ссылка открыта: {action.url}"

    if isinstance(action, CopyAction):
        pyperclip.copy(action.text)

        if action.notification:
            shown = _emit_notification("PContext", action.notification)
            if shown:
                return "Текст скопирован в буфер обмена. Уведомление показано."
            return f"Текст скопирован в буфер обмена. Сообщение: {action.notification}"

        return "Текст скопирован в буфер обмена."

    if isinstance(action, TextAction):
        shown = _emit_text(action.title, action.text)
        if shown:
            return "Текст показан в отдельном окне."

        return (
            "Скрипт вернул Text. Полноценное окно показа текста "
            "доступно только при запуске GUI-версии PContext."
        )

    if isinstance(action, NotifyAction):
        shown = _emit_notification(action.title, action.description)
        if shown:
            return f"Уведомление показано: {action.title}"

        return (
            f"Скрипт вернул Notify ('{action.title}'). "
            "Нативные уведомления доступны только при запуске GUI-версии PContext."
        )

    raise TypeError("Получено неподдерживаемое сериализованное действие.")
