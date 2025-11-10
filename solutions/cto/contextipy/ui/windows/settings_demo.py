"""Demo script for the settings window."""

from __future__ import annotations

import sys

try:
    from PySide6.QtWidgets import QApplication
except ImportError:
    print("PySide6 is required to run this demo")
    sys.exit(1)

from contextipy.config.settings import Settings, SettingsStore
from contextipy.os_integration.autostart import disable_autostart, enable_autostart
from contextipy.ui.theme import initialize_theme
from contextipy.ui.windows.settings import SettingsWindow


def on_autostart_change(enabled: bool) -> tuple[bool, str | None]:
    """Handle auto-start change."""
    if enabled:
        result = enable_autostart(app_name="ContextiPY")
    else:
        result = disable_autostart(app_name="ContextiPY")

    if result.success:
        return (True, None)
    return (False, result.error)


def main() -> None:
    """Run the settings window demo."""
    app = QApplication(sys.argv)
    initialize_theme(app)

    settings_store = SettingsStore()

    window = SettingsWindow(
        settings_store=settings_store,
        on_autostart_change=on_autostart_change,
    )
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
