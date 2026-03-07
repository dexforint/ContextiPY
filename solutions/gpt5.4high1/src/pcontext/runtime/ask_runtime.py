from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass

from pcontext.runtime.question_models import QuestionFormSchema


@dataclass(frozen=True, slots=True)
class AskExecutionHooks:
    """
    GUI-хуки для Ask(...).

    Через них агент может попросить GUI-поток открыть модальное окно
    и дождаться ответа пользователя.
    """

    ask_user: Callable[[QuestionFormSchema], dict[str, object] | None] | None = None


_HOOKS_LOCK = threading.RLock()
_ACTIVE_HOOKS: AskExecutionHooks | None = None


def install_ask_execution_hooks(hooks: AskExecutionHooks | None) -> None:
    """
    Устанавливает или сбрасывает Ask-хуки.
    """
    global _ACTIVE_HOOKS

    with _HOOKS_LOCK:
        _ACTIVE_HOOKS = hooks


def clear_ask_execution_hooks() -> None:
    """
    Полностью удаляет установленные Ask-хуки.
    """
    install_ask_execution_hooks(None)


def request_user_answers(schema: QuestionFormSchema) -> dict[str, object] | None:
    """
    Просит GUI-слой показать форму и вернуть ответы пользователя.

    Если GUI-хук не установлен, Ask(...) в текущем процессе недоступен.
    """
    with _HOOKS_LOCK:
        hooks = _ACTIVE_HOOKS

    if hooks is None or hooks.ask_user is None:
        raise RuntimeError(
            "Ask(...) доступен только при запущенном GUI-режиме PContext."
        )

    return hooks.ask_user(schema)
