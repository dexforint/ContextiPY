"""System tray icon and menu for Contextipy application.

This module provides the main QSystemTrayIcon with a Russian-language context menu,
integrates with Settings for notification preferences, and manages the application
lifecycle including minimize-to-tray and clean exit with service shutdown.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

try:  # pragma: no cover
    from PySide6.QtCore import QObject, Signal
    from PySide6.QtGui import QAction, QIcon
    from PySide6.QtWidgets import QMenu, QSystemTrayIcon
except ImportError:  # pragma: no cover
    QObject = object  # type: ignore[assignment,misc]
    Signal = object  # type: ignore[assignment,misc]
    QAction = object  # type: ignore[assignment,misc]
    QIcon = object  # type: ignore[assignment,misc]
    QMenu = object  # type: ignore[assignment,misc]
    QSystemTrayIcon = object  # type: ignore[assignment,misc]
    PYSIDE_AVAILABLE = False
else:
    PYSIDE_AVAILABLE = True

if TYPE_CHECKING:
    from contextipy.config.settings import Settings, SettingsStore
    from contextipy.execution.service_manager import ServiceManager
    from contextipy.logging.logger import ExecutionLogger
    from contextipy.utils.notifications import NotificationCenter


class _TrayLogHandler(logging.Handler):
    """Log handler that forwards warning/error records to tray notifications."""

    def __init__(self, tray: "TrayApplication") -> None:
        super().__init__(level=logging.WARNING)
        self._tray = tray

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401 - inherited docstring
        if not self._tray.notifications_enabled:
            return

        try:
            message = self.format(record)
            title = record.levelname.title()
            if record.levelno >= logging.ERROR:
                self._tray.show_error_notification(title, message)
            else:
                self._tray.show_warning_notification(title, message)
        except Exception:  # pragma: no cover - guard against handler failures
            self.handleError(record)


class TrayApplication(QObject):
    """System tray application with context menu and lifecycle management.

    This class manages the system tray icon with a Russian-language context menu,
    integrates with Settings for notification preferences, handles balloon
    notifications via logging hooks, and manages application lifecycle including
    minimize-to-tray and clean exit with service shutdown.

    Signals:
        show_running_services: Request to show running services window
        show_processes: Request to show processes window
        show_all_scripts_services: Request to show all scripts and services window
        show_settings: Request to show settings window
        show_logs: Request to show logs window
        quit_requested: Request to quit the application
    """

    show_running_services: Signal = Signal()  # type: ignore[assignment]
    show_processes: Signal = Signal()  # type: ignore[assignment]
    show_all_scripts_services: Signal = Signal()  # type: ignore[assignment]
    show_settings: Signal = Signal()  # type: ignore[assignment]
    show_logs: Signal = Signal()  # type: ignore[assignment]
    quit_requested: Signal = Signal()  # type: ignore[assignment]

    def __init__(
        self,
        icon: QIcon | None = None,
        *,
        settings_store: SettingsStore | None = None,
        service_manager: ServiceManager | None = None,
        execution_logger: ExecutionLogger | None = None,
        notification_center: NotificationCenter | None = None,
    ) -> None:
        """Initialize the tray application.

        Args:
            icon: Optional icon for the tray. If None, uses default app icon.
            settings_store: Optional settings store for notification preferences.
            service_manager: Optional service manager for stopping services on quit.
            execution_logger: Optional execution logger for log notifications.
            notification_center: Optional notification center for balloon messages.
        """
        if not PYSIDE_AVAILABLE:
            raise RuntimeError("PySide6 is not available")

        super().__init__()

        self._settings_store = settings_store
        self._service_manager = service_manager
        self._execution_logger = execution_logger
        self._notification_center = notification_center

        self._log_handler: _TrayLogHandler | None = None
        self._log_logger: logging.Logger | None = None

        # Load initial settings
        self._current_settings: Settings | None = None
        if self._settings_store:
            self._current_settings = self._settings_store.load()
            self._settings_store.on_change(self._on_settings_changed)

        # Create system tray icon
        self._tray_icon = QSystemTrayIcon(self)
        if icon is not None and not icon.isNull():
            self._tray_icon.setIcon(icon)
        else:
            from .icons import APP_ICON_NAME, load_icon

            default_icon = load_icon(APP_ICON_NAME)
            if not default_icon.isNull():
                self._tray_icon.setIcon(default_icon)

        # Create context menu
        self._menu = self._create_menu()
        self._tray_icon.setContextMenu(self._menu)

        # Set tooltip
        self._tray_icon.setToolTip("Contextipy")

        # Connect tray icon signals
        self._tray_icon.activated.connect(self._on_tray_activated)

        # Show the tray icon
        self._tray_icon.show()

        # Set up notification center with tray icon
        if self._notification_center:
            self._notification_center.set_tray_icon(self._tray_icon)

        # Set up logging handler for tray notifications
        self._log_handler = _TrayLogHandler(self)
        self._log_handler.addFilter(logging.Filter("contextipy"))
        self._log_handler.setFormatter(logging.Formatter("%(message)s"))
        self._log_logger = logging.getLogger()
        self._log_logger.addHandler(self._log_handler)

    @property
    def notifications_enabled(self) -> bool:
        """Check if notifications are currently enabled.

        Returns:
            True if notifications are enabled, False otherwise.
        """
        return not self._current_settings or self._current_settings.enable_notifications

    def _create_menu(self) -> QMenu:
        """Create the context menu with Russian-language entries."""
        menu = QMenu()

        # Запущенные сервисы (Running Services)
        running_services_action = QAction("Запущенные сервисы", self)
        running_services_action.triggered.connect(self.show_running_services.emit)
        menu.addAction(running_services_action)

        # Процессы (Processes)
        processes_action = QAction("Процессы", self)
        processes_action.triggered.connect(self.show_processes.emit)
        menu.addAction(processes_action)

        # Все скрипты и сервисы (All Scripts and Services)
        all_scripts_action = QAction("Все скрипты и сервисы", self)
        all_scripts_action.triggered.connect(self.show_all_scripts_services.emit)
        menu.addAction(all_scripts_action)

        menu.addSeparator()

        # Настройки (Settings)
        settings_action = QAction("Настройки", self)
        settings_action.triggered.connect(self.show_settings.emit)
        menu.addAction(settings_action)

        # Логи (Logs)
        logs_action = QAction("Логи", self)
        logs_action.triggered.connect(self.show_logs.emit)
        menu.addAction(logs_action)

        menu.addSeparator()

        # Выход (Exit)
        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(self._on_quit_triggered)
        menu.addAction(quit_action)

        return menu

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation.

        Args:
            reason: The activation reason (e.g., double-click, trigger).
        """
        # On double-click, show the all scripts and services window
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_all_scripts_services.emit()

    def _on_settings_changed(self, settings: Settings) -> None:
        """Handle settings changes.

        Args:
            settings: The updated settings instance.
        """
        self._current_settings = settings

        # Update notification center if notifications were toggled
        # The notification center checks settings internally via is_suppressed

    def _on_quit_triggered(self) -> None:
        """Handle quit action from the tray menu."""
        # Stop all services before quitting
        if self._service_manager:
            try:
                self._service_manager.shutdown()
            except Exception:
                pass

        # Stop notification center worker thread
        if self._notification_center:
            try:
                self._notification_center.stop()
            except Exception:
                pass

        # Emit quit requested signal
        self.quit_requested.emit()

        # Hide and cleanup the tray icon
        self._tray_icon.hide()

    def show_notification(
        self,
        title: str,
        message: str | None = None,
        *,
        icon: QSystemTrayIcon.MessageIcon | None = None,
        duration: int = 5000,
    ) -> None:
        """Show a balloon notification from the tray icon.

        Args:
            title: Notification title.
            message: Optional notification message.
            icon: Optional icon type for the notification.
            duration: Duration to show the notification in milliseconds (default: 5000).
        """
        if not self.notifications_enabled:
            return

        icon_type = icon if icon is not None else QSystemTrayIcon.MessageIcon.Information
        self._tray_icon.showMessage(title, message or "", icon_type, duration)

    def show_error_notification(self, title: str, message: str | None = None) -> None:
        """Show an error balloon notification from the tray icon.

        Args:
            title: Notification title.
            message: Optional notification message.
        """
        self.show_notification(
            title, message, icon=QSystemTrayIcon.MessageIcon.Critical, duration=10000
        )

    def show_warning_notification(self, title: str, message: str | None = None) -> None:
        """Show a warning balloon notification from the tray icon.

        Args:
            title: Notification title.
            message: Optional notification message.
        """
        self.show_notification(
            title, message, icon=QSystemTrayIcon.MessageIcon.Warning, duration=7000
        )

    def hide_tray_icon(self) -> None:
        """Hide the tray icon."""
        self._tray_icon.hide()

    def show_tray_icon(self) -> None:
        """Show the tray icon."""
        self._tray_icon.show()

    def is_visible(self) -> bool:
        """Check if the tray icon is visible.

        Returns:
            True if the tray icon is visible, False otherwise.
        """
        return self._tray_icon.isVisible()

    def cleanup(self) -> None:
        """Clean up resources and hide the tray icon."""
        # Remove log handler
        if self._log_logger and self._log_handler:
            try:
                self._log_logger.removeHandler(self._log_handler)
                self._log_handler.close()
            except Exception:
                pass
            finally:
                self._log_handler = None
                self._log_logger = None

        # Stop services
        if self._service_manager:
            try:
                self._service_manager.shutdown()
            except Exception:
                pass

        # Stop notification center
        if self._notification_center:
            try:
                self._notification_center.stop()
            except Exception:
                pass

        # Remove settings listener
        if self._settings_store:
            try:
                self._settings_store.remove_listener(self._on_settings_changed)
            except Exception:
                pass

        # Hide tray icon
        self._tray_icon.hide()


def create_tray_application(
    icon: QIcon | None = None,
    *,
    settings_store: SettingsStore | None = None,
    service_manager: ServiceManager | None = None,
    execution_logger: ExecutionLogger | None = None,
    notification_center: NotificationCenter | None = None,
) -> TrayApplication:
    """Factory function to create a TrayApplication instance.

    Args:
        icon: Optional icon for the tray. If None, uses default app icon.
        settings_store: Optional settings store for notification preferences.
        service_manager: Optional service manager for stopping services on quit.
        execution_logger: Optional execution logger for log notifications.
        notification_center: Optional notification center for balloon messages.

    Returns:
        A configured TrayApplication instance.
    """
    return TrayApplication(
        icon=icon,
        settings_store=settings_store,
        service_manager=service_manager,
        execution_logger=execution_logger,
        notification_center=notification_center,
    )


__all__ = ["TrayApplication", "create_tray_application"]
