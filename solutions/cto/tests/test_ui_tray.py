"""Tests for the system tray UI component."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, Mock, patch

import pytest

if TYPE_CHECKING:
    from contextipy.config.settings import Settings, SettingsStore
    from contextipy.execution.service_manager import ServiceManager
    from contextipy.logging.logger import ExecutionLogger
    from contextipy.ui.tray import TrayApplication
    from contextipy.utils.notifications import NotificationCenter

try:
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication, QSystemTrayIcon

    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False
    pytest.skip("PySide6 not available", allow_module_level=True)


@pytest.fixture
def qapp() -> QApplication:
    """Provide a QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def mock_settings_store() -> Mock:
    """Provide a mock SettingsStore."""
    store = Mock()
    settings = Mock()
    settings.enable_notifications = True
    settings.launch_on_startup = False
    store.load.return_value = settings
    store.on_change = Mock()
    store.remove_listener = Mock()
    return store


@pytest.fixture
def mock_service_manager() -> Mock:
    """Provide a mock ServiceManager."""
    manager = Mock()
    manager.shutdown = Mock()
    return manager


@pytest.fixture
def mock_execution_logger() -> Mock:
    """Provide a mock ExecutionLogger."""
    logger = Mock()
    return logger


@pytest.fixture
def mock_notification_center() -> Mock:
    """Provide a mock NotificationCenter."""
    center = Mock()
    center.set_tray_icon = Mock()
    center.stop = Mock()
    return center


@pytest.fixture
def tray_app(
    qapp: QApplication,
    mock_settings_store: Mock,
    mock_service_manager: Mock,
    mock_execution_logger: Mock,
    mock_notification_center: Mock,
) -> TrayApplication:
    """Provide a TrayApplication instance with mocked dependencies."""
    from contextipy.ui.tray import TrayApplication

    tray = TrayApplication(
        settings_store=mock_settings_store,
        service_manager=mock_service_manager,
        execution_logger=mock_execution_logger,
        notification_center=mock_notification_center,
    )
    yield tray
    tray.cleanup()


def test_tray_application_init(tray_app: TrayApplication) -> None:
    """Test that TrayApplication initializes correctly."""
    assert tray_app is not None
    assert tray_app.is_visible()


def test_tray_application_with_icon(qapp: QApplication) -> None:
    """Test that TrayApplication can be initialized with a custom icon."""
    from contextipy.ui.icons import create_placeholder_icon
    from contextipy.ui.tray import TrayApplication

    icon = create_placeholder_icon()
    tray_app = TrayApplication(icon=icon)

    assert tray_app is not None
    assert tray_app.is_visible()


def test_tray_application_signals(tray_app: TrayApplication) -> None:
    """Test that TrayApplication has all expected signals."""
    assert hasattr(tray_app, "show_running_services")
    assert hasattr(tray_app, "show_processes")
    assert hasattr(tray_app, "show_all_scripts_services")
    assert hasattr(tray_app, "show_settings")
    assert hasattr(tray_app, "show_logs")
    assert hasattr(tray_app, "quit_requested")


def test_tray_menu_actions(tray_app: TrayApplication) -> None:
    """Test that the tray menu has all expected actions."""
    menu = tray_app._menu
    actions = menu.actions()

    action_texts = [action.text() for action in actions]

    # Check for Russian menu entries
    assert "Запущенные сервисы" in action_texts
    assert "Процессы" in action_texts
    assert "Все скрипты и сервисы" in action_texts
    assert "Настройки" in action_texts
    assert "Логи" in action_texts
    assert "Выход" in action_texts


def test_signal_emission_running_services(tray_app: TrayApplication) -> None:
    """Test that the running services action emits the correct signal."""
    signal_emitted = False

    def handler() -> None:
        nonlocal signal_emitted
        signal_emitted = True

    tray_app.show_running_services.connect(handler)

    # Find and trigger the action
    actions = tray_app._menu.actions()
    for action in actions:
        if action.text() == "Запущенные сервисы":
            action.trigger()
            break

    assert signal_emitted


def test_signal_emission_processes(tray_app: TrayApplication) -> None:
    """Test that the processes action emits the correct signal."""
    signal_emitted = False

    def handler() -> None:
        nonlocal signal_emitted
        signal_emitted = True

    tray_app.show_processes.connect(handler)

    actions = tray_app._menu.actions()
    for action in actions:
        if action.text() == "Процессы":
            action.trigger()
            break

    assert signal_emitted


def test_signal_emission_all_scripts(tray_app: TrayApplication) -> None:
    """Test that the all scripts action emits the correct signal."""
    signal_emitted = False

    def handler() -> None:
        nonlocal signal_emitted
        signal_emitted = True

    tray_app.show_all_scripts_services.connect(handler)

    actions = tray_app._menu.actions()
    for action in actions:
        if action.text() == "Все скрипты и сервисы":
            action.trigger()
            break

    assert signal_emitted


def test_signal_emission_settings(tray_app: TrayApplication) -> None:
    """Test that the settings action emits the correct signal."""
    signal_emitted = False

    def handler() -> None:
        nonlocal signal_emitted
        signal_emitted = True

    tray_app.show_settings.connect(handler)

    actions = tray_app._menu.actions()
    for action in actions:
        if action.text() == "Настройки":
            action.trigger()
            break

    assert signal_emitted


def test_signal_emission_logs(tray_app: TrayApplication) -> None:
    """Test that the logs action emits the correct signal."""
    signal_emitted = False

    def handler() -> None:
        nonlocal signal_emitted
        signal_emitted = True

    tray_app.show_logs.connect(handler)

    actions = tray_app._menu.actions()
    for action in actions:
        if action.text() == "Логи":
            action.trigger()
            break

    assert signal_emitted


def test_quit_action_stops_services(
    tray_app: TrayApplication, mock_service_manager: Mock
) -> None:
    """Test that the quit action stops all services."""
    actions = tray_app._menu.actions()
    for action in actions:
        if action.text() == "Выход":
            action.trigger()
            break

    mock_service_manager.shutdown.assert_called_once()


def test_quit_action_stops_notifications(
    tray_app: TrayApplication, mock_notification_center: Mock
) -> None:
    """Test that the quit action stops the notification center."""
    actions = tray_app._menu.actions()
    for action in actions:
        if action.text() == "Выход":
            action.trigger()
            break

    mock_notification_center.stop.assert_called_once()


def test_quit_action_emits_signal(tray_app: TrayApplication) -> None:
    """Test that the quit action emits the quit_requested signal."""
    signal_emitted = False

    def handler() -> None:
        nonlocal signal_emitted
        signal_emitted = True

    tray_app.quit_requested.connect(handler)

    actions = tray_app._menu.actions()
    for action in actions:
        if action.text() == "Выход":
            action.trigger()
            break

    assert signal_emitted


def test_settings_change_handler(tray_app: TrayApplication, mock_settings_store: Mock) -> None:
    """Test that settings changes are properly handled."""
    new_settings = Mock()
    new_settings.enable_notifications = False
    new_settings.launch_on_startup = True

    # Simulate settings change callback
    tray_app._on_settings_changed(new_settings)

    assert tray_app._current_settings == new_settings


def test_show_notification_when_enabled(tray_app: TrayApplication) -> None:
    """Test showing a notification when notifications are enabled."""
    # Notifications are enabled by default in the mock
    with patch.object(tray_app._tray_icon, "showMessage") as mock_show:
        tray_app.show_notification("Test Title", "Test Message")
        mock_show.assert_called_once()


def test_show_notification_when_disabled(
    tray_app: TrayApplication, mock_settings_store: Mock
) -> None:
    """Test showing a notification when notifications are disabled."""
    # Disable notifications
    disabled_settings = Mock()
    disabled_settings.enable_notifications = False
    tray_app._on_settings_changed(disabled_settings)

    with patch.object(tray_app._tray_icon, "showMessage") as mock_show:
        tray_app.show_notification("Test Title", "Test Message")
        # Should NOT show when disabled
        mock_show.assert_not_called()


def test_show_error_notification(tray_app: TrayApplication) -> None:
    """Test showing an error notification."""
    with patch.object(tray_app._tray_icon, "showMessage") as mock_show:
        tray_app.show_error_notification("Error Title", "Error Message")
        mock_show.assert_called_once()
        # Check that it uses the Critical icon
        call_args = mock_show.call_args
        assert call_args[0][3] == QSystemTrayIcon.MessageIcon.Critical


def test_show_warning_notification(tray_app: TrayApplication) -> None:
    """Test showing a warning notification."""
    with patch.object(tray_app._tray_icon, "showMessage") as mock_show:
        tray_app.show_warning_notification("Warning Title", "Warning Message")
        mock_show.assert_called_once()
        # Check that it uses the Warning icon
        call_args = mock_show.call_args
        assert call_args[0][3] == QSystemTrayIcon.MessageIcon.Warning


def test_hide_tray_icon(tray_app: TrayApplication) -> None:
    """Test hiding the tray icon."""
    tray_app.hide_tray_icon()
    assert not tray_app.is_visible()


def test_show_tray_icon(tray_app: TrayApplication) -> None:
    """Test showing the tray icon after hiding."""
    tray_app.hide_tray_icon()
    tray_app.show_tray_icon()
    assert tray_app.is_visible()


def test_cleanup(
    tray_app: TrayApplication,
    mock_service_manager: Mock,
    mock_notification_center: Mock,
    mock_settings_store: Mock,
) -> None:
    """Test cleanup method."""
    tray_app.cleanup()

    mock_service_manager.shutdown.assert_called_once()
    mock_notification_center.stop.assert_called_once()
    mock_settings_store.remove_listener.assert_called_once()
    assert not tray_app.is_visible()


def test_cleanup_handles_exceptions(tray_app: TrayApplication) -> None:
    """Test that cleanup handles exceptions gracefully."""
    # Make service manager raise an exception
    tray_app._service_manager.shutdown.side_effect = Exception("Test error")

    # Should not raise an exception
    tray_app.cleanup()


def test_notification_center_integration(
    qapp: QApplication,
    mock_notification_center: Mock,
) -> None:
    """Test that notification center is set up with tray icon."""
    from contextipy.ui.tray import TrayApplication

    tray_app = TrayApplication(notification_center=mock_notification_center)

    mock_notification_center.set_tray_icon.assert_called_once()


def test_tray_activation_double_click(tray_app: TrayApplication) -> None:
    """Test that double-clicking the tray icon shows all scripts."""
    signal_emitted = False

    def handler() -> None:
        nonlocal signal_emitted
        signal_emitted = True

    tray_app.show_all_scripts_services.connect(handler)

    # Simulate double-click
    tray_app._on_tray_activated(QSystemTrayIcon.ActivationReason.DoubleClick)

    assert signal_emitted


def test_create_tray_application_factory() -> None:
    """Test the factory function for creating a TrayApplication."""
    from contextipy.ui.tray import create_tray_application

    tray_app = create_tray_application()

    assert tray_app is not None
    assert isinstance(tray_app, TrayApplication)


def test_create_tray_application_with_deps() -> None:
    """Test the factory function with dependencies."""
    from contextipy.ui.tray import create_tray_application

    mock_store = Mock()
    mock_manager = Mock()
    mock_logger = Mock()
    mock_center = Mock()

    tray_app = create_tray_application(
        settings_store=mock_store,
        service_manager=mock_manager,
        execution_logger=mock_logger,
        notification_center=mock_center,
    )

    assert tray_app is not None
    assert tray_app._settings_store == mock_store
    assert tray_app._service_manager == mock_manager
    assert tray_app._execution_logger == mock_logger
    assert tray_app._notification_center == mock_center


def test_tray_application_without_pyside():
    """Test that TrayApplication raises error without PySide6."""
    with patch("contextipy.ui.tray.PYSIDE_AVAILABLE", False):
        from contextipy.ui.tray import TrayApplication

        with pytest.raises(RuntimeError, match="PySide6 is not available"):
            TrayApplication()


def test_logging_integration_error(tray_app: TrayApplication) -> None:
    """Test that error logs trigger error notifications."""
    import logging

    with patch.object(tray_app, "show_error_notification") as mock_error:
        logger = logging.getLogger("contextipy.test")
        logger.error("Test error message")
        # Give the handler a moment to process
        mock_error.assert_called_once()


def test_logging_integration_warning(tray_app: TrayApplication) -> None:
    """Test that warning logs trigger warning notifications."""
    import logging

    with patch.object(tray_app, "show_warning_notification") as mock_warning:
        logger = logging.getLogger("contextipy.test")
        logger.warning("Test warning message")
        # Give the handler a moment to process
        mock_warning.assert_called_once()


def test_logging_integration_respects_settings(
    tray_app: TrayApplication, mock_settings_store: Mock
) -> None:
    """Test that logging integration respects notification settings."""
    import logging

    # Disable notifications
    disabled_settings = Mock()
    disabled_settings.enable_notifications = False
    tray_app._on_settings_changed(disabled_settings)

    with patch.object(tray_app, "show_error_notification") as mock_error:
        logger = logging.getLogger("contextipy.test")
        logger.error("Test error message")
        # Should not call notification when disabled
        mock_error.assert_not_called()


def test_notifications_enabled_property(tray_app: TrayApplication) -> None:
    """Test the notifications_enabled property."""
    # Default is enabled
    assert tray_app.notifications_enabled

    # Disable
    disabled_settings = Mock()
    disabled_settings.enable_notifications = False
    tray_app._on_settings_changed(disabled_settings)
    assert not tray_app.notifications_enabled

    # Re-enable
    enabled_settings = Mock()
    enabled_settings.enable_notifications = True
    tray_app._on_settings_changed(enabled_settings)
    assert tray_app.notifications_enabled
