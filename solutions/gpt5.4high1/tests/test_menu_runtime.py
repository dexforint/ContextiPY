from __future__ import annotations

from pcontext.runtime.menu_runtime import (
    ChooserItem,
    MenuExecutionHooks,
    clear_menu_execution_hooks,
    install_menu_execution_hooks,
    request_menu_choice,
)


def test_request_menu_choice_uses_installed_hook() -> None:
    """
    Выбор launcher-меню должен уходить в установленный GUI-hook.
    """
    calls: list[tuple[str | None, list[str]]] = []

    install_menu_execution_hooks(
        MenuExecutionHooks(
            choose_menu_item=lambda current_folder, items: (
                calls.append((current_folder, [item.id for item in items])),
                items[0].id,
            )[1],
        )
    )

    try:
        result = request_menu_choice(
            "C:/tmp",
            [
                ChooserItem(
                    id="a",
                    title="A",
                    description=None,
                    kind="oneshot_script",
                    service_title=None,
                    updated_at_utc=None,
                    launch_count=0,
                    last_used_utc=None,
                ),
                ChooserItem(
                    id="b",
                    title="B",
                    description=None,
                    kind="service_script",
                    service_title="Service",
                    updated_at_utc=None,
                    launch_count=1,
                    last_used_utc=None,
                ),
            ],
        )

        assert result == "a"
        assert calls == [("C:/tmp", ["a", "b"])]
    finally:
        clear_menu_execution_hooks()
