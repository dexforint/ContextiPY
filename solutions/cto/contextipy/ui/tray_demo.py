"""Demo application showcasing the system tray integration.

This demo demonstrates the full lifecycle of the TrayApplication including:
- System tray icon with context menu
- Russian-language menu entries
- Signal handling for menu actions
- Integration with Settings for notification preferences
- Service lifecycle management on quit
- Balloon notifications from the tray

Usage:
    python -m contextipy.ui.tray_demo
"""

from __future__ import annotations

import sys
from typing import Sequence

try:  # pragma: no cover
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget
except ImportError:  # pragma: no cover
    print("PySide6 is required to run this demo")
    sys.exit(1)

from contextipy.config.settings import SettingsStore
from contextipy.ui.application import ensure_application, exit_application
from contextipy.ui.icons import APP_ICON_NAME, load_icon
from contextipy.ui.theme import get_theme
from contextipy.ui.tray import TrayApplication
from contextipy.ui.widgets import Heading, PrimaryButton, SecondaryLabel, VStack
from contextipy.utils.notifications import get_notification_center


class PlaceholderWindow(QMainWindow):
    """Placeholder window for demonstrating tray menu actions."""

    def __init__(self, title: str, description: str) -> None:
        """Initialize the placeholder window.

        Args:
            title: Window title.
            description: Window description text.
        """
        super().__init__()
        theme = get_theme()
        spacing = theme.spacing

        self.setWindowTitle(title)
        self.setMinimumSize(500, 300)

        icon = load_icon(APP_ICON_NAME)
        if not icon.isNull():
            self.setWindowIcon(icon)

        central_widget = QWidget(self)
        central_layout = QVBoxLayout(central_widget)
        central_layout.setSpacing(spacing.lg)
        central_layout.setContentsMargins(spacing.xl, spacing.xl, spacing.xl, spacing.xl)

        header = Heading(title, level=1)
        header.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        central_layout.addWidget(header)

        desc_label = SecondaryLabel(description)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        desc_label.setWordWrap(True)
        central_layout.addWidget(desc_label)

        close_button = PrimaryButton("Close Window")
        close_button.clicked.connect(self.hide)
        central_layout.addWidget(close_button)

        central_layout.addStretch(1)

        self.setCentralWidget(central_widget)


class TrayDemo:
    """Main demo application showcasing the system tray integration."""

    def __init__(self) -> None:
        """Initialize the demo application."""
        # Ensure application exists
        self.app = ensure_application()

        # Set up settings store
        self.settings_store = SettingsStore()

        # Set up notification center
        self.notification_center = get_notification_center(settings_provider=self.settings_store)

        # Create tray application
        self.tray = TrayApplication(
            settings_store=self.settings_store,
            notification_center=self.notification_center,
        )

        # Connect signals to handlers
        self.tray.show_running_services.connect(self._show_running_services)
        self.tray.show_processes.connect(self._show_processes)
        self.tray.show_all_scripts_services.connect(self._show_all_scripts)
        self.tray.show_settings.connect(self._show_settings)
        self.tray.show_logs.connect(self._show_logs)
        self.tray.quit_requested.connect(self._on_quit)

        # Create placeholder windows
        self._running_services_window: PlaceholderWindow | None = None
        self._processes_window: PlaceholderWindow | None = None
        self._all_scripts_window: PlaceholderWindow | None = None
        self._settings_window: PlaceholderWindow | None = None
        self._logs_window: PlaceholderWindow | None = None

        # Show welcome notification
        self.tray.show_notification(
            "Contextipy Started",
            "Contextipy is now running in the system tray. Right-click the icon for options.",
        )

    def _show_running_services(self) -> None:
        """Show the running services window."""
        if self._running_services_window is None:
            self._running_services_window = PlaceholderWindow(
                "Запущенные сервисы",
                "This window would show all currently running services.\n\n"
                "Services would be listed here with their status, uptime, "
                "and controls to stop or restart them.",
            )
        self._running_services_window.show()
        self._running_services_window.raise_()
        self._running_services_window.activateWindow()

    def _show_processes(self) -> None:
        """Show the processes window."""
        if self._processes_window is None:
            self._processes_window = PlaceholderWindow(
                "Процессы",
                "This window would show all running processes.\n\n"
                "Process information including PID, CPU usage, memory usage, "
                "and controls to terminate processes would be displayed here.",
            )
        self._processes_window.show()
        self._processes_window.raise_()
        self._processes_window.activateWindow()

    def _show_all_scripts(self) -> None:
        """Show the all scripts and services window."""
        if self._all_scripts_window is None:
            self._all_scripts_window = PlaceholderWindow(
                "Все скрипты и сервисы",
                "This window would show all available scripts and services.\n\n"
                "Users could browse, search, and launch scripts, view service definitions, "
                "and configure startup behavior from this main window.",
            )
        self._all_scripts_window.show()
        self._all_scripts_window.raise_()
        self._all_scripts_window.activateWindow()

    def _show_settings(self) -> None:
        """Show the settings window."""
        if self._settings_window is None:
            self._settings_window = PlaceholderWindow(
                "Настройки",
                "This window would display application settings.\n\n"
                "Settings include notification preferences, startup behavior, "
                "theme selection, and other configuration options.",
            )
        self._settings_window.show()
        self._settings_window.raise_()
        self._settings_window.activateWindow()

    def _show_logs(self) -> None:
        """Show the logs window."""
        if self._logs_window is None:
            self._logs_window = PlaceholderWindow(
                "Логи",
                "This window would display execution logs.\n\n"
                "Logs would show recent script executions, their status, output, "
                "and allow filtering by status, script, or time range.",
            )
        self._logs_window.show()
        self._logs_window.raise_()
        self._logs_window.activateWindow()

    def _on_quit(self) -> None:
        """Handle quit request."""
        # Clean up tray
        self.tray.cleanup()

        # Exit application
        exit_application()

    def run(self) -> int:
        """Run the demo application.

        Returns:
            Application exit code.
        """
        return self.app.exec()


def main(argv: Sequence[str] | None = None) -> int:
    """Launch the tray demo application.

    Args:
        argv: Command-line arguments (optional).

    Returns:
        Application exit code.
    """
    demo = TrayDemo()
    return demo.run()


if __name__ == "__main__":
    raise SystemExit(main())
