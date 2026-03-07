from __future__ import annotations

from pcontext.runtime.action_codec import CopyAction, NotifyAction, TextAction
from pcontext.runtime.action_executor import (
    ActionExecutionHooks,
    clear_action_execution_hooks,
    execute_serialized_action,
    install_action_execution_hooks,
)


def test_text_action_uses_installed_hooks() -> None:
    """
    Действие Text должно уходить в установленный GUI-hook.
    """
    calls: list[tuple[str | None, str]] = []

    install_action_execution_hooks(
        ActionExecutionHooks(
            show_text=lambda title, text: calls.append((title, text)),
        )
    )

    try:
        message = execute_serialized_action(
            TextAction(
                title="My title",
                text="Hello from test",
            )
        )

        assert calls == [("My title", "Hello from test")]
        assert "Текст показан" in message
    finally:
        clear_action_execution_hooks()


def test_notify_and_copy_notification_use_installed_hooks(monkeypatch) -> None:
    """
    Notify и Copy(notification=...) должны использовать GUI-hook уведомлений.
    """
    copied_texts: list[str] = []
    notifications: list[tuple[str, str | None]] = []

    monkeypatch.setattr(
        "pcontext.runtime.action_executor.pyperclip.copy",
        lambda text: copied_texts.append(text),
    )

    install_action_execution_hooks(
        ActionExecutionHooks(
            show_notification=lambda title, description: notifications.append(
                (title, description)
            ),
        )
    )

    try:
        copy_message = execute_serialized_action(
            CopyAction(
                text="copied value",
                notification="Copied successfully",
            )
        )
        notify_message = execute_serialized_action(
            NotifyAction(
                title="Notify title",
                description="Notify body",
            )
        )

        assert copied_texts == ["copied value"]
        assert ("PContext", "Copied successfully") in notifications
        assert ("Notify title", "Notify body") in notifications
        assert "Уведомление" in notify_message
        assert "буфер" in copy_message
    finally:
        clear_action_execution_hooks()
