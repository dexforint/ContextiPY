from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal


ChooserRegistrationStatus = Literal["registered", "error", "untracked"]


@dataclass(frozen=True, slots=True)
class ChooserItem:
    """
    Расширенное описание команды для GUI chooser.
    """

    id: str
    title: str
    description: str | None
    kind: Literal["oneshot_script", "service_script"]
    service_title: str | None
    updated_at_utc: str | None
    launch_count: int
    last_used_utc: str | None
    enabled: bool = True
    has_parameters: bool = False
    icon_name: str | None = None
    registration_status: ChooserRegistrationStatus = "registered"


@dataclass(frozen=True, slots=True)
class MenuExecutionHooks:
    """
    GUI-хуки для выбора пункта меню из launcher-процесса.
    """

    choose_menu_item: Callable[[str | None, list[ChooserItem]], str | None] | None = (
        None
    )


_HOOKS_LOCK = threading.RLock()
_ACTIVE_HOOKS: MenuExecutionHooks | None = None


def install_menu_execution_hooks(hooks: MenuExecutionHooks | None) -> None:
    """
    Устанавливает или сбрасывает menu-хуки.
    """
    global _ACTIVE_HOOKS

    with _HOOKS_LOCK:
        _ACTIVE_HOOKS = hooks


def clear_menu_execution_hooks() -> None:
    """
    Полностью удаляет установленные menu-хуки.
    """
    install_menu_execution_hooks(None)


def request_menu_choice(
    current_folder: str | None,
    items: list[ChooserItem],
) -> str | None:
    """
    Просит GUI показать chooser и вернуть id выбранного пункта.
    """
    with _HOOKS_LOCK:
        hooks = _ACTIVE_HOOKS

    if hooks is None or hooks.choose_menu_item is None:
        raise RuntimeError(
            "Выбор пункта меню из launcher доступен только при запущенном GUI-режиме PContext."
        )

    return hooks.choose_menu_item(current_folder, items)
