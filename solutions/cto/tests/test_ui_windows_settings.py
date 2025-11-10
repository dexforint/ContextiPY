"""Tests for settings window."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

try:
    from PySide6.QtWidgets import QApplication

    PYSIDE_AVAILABLE = True
except ImportError:  # pragma: no cover
    PYSIDE_AVAILABLE = False

pytestmark = pytest.mark.skipif(not PYSIDE_AVAILABLE, reason="PySide6 not available")


@pytest.fixture
def qapp() -> QApplication:
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_settings_window_loads_settings(qapp):
    """Test that SettingsWindow loads current settings."""
    from contextipy.config.settings import Settings
    from contextipy.ui.windows.settings import SettingsWindow

    load_settings = Mock(return_value=Settings(launch_on_startup=True, enable_notifications=False))

    window = SettingsWindow(load_settings=load_settings)

    assert window is not None
    load_settings.assert_called_once()

    assert window._checkboxes["launch_on_startup"].isChecked() is True
    assert window._checkboxes["enable_notifications"].isChecked() is False


def test_settings_window_save_success(qapp):
    """Test saving settings with success."""
    from contextipy.config.settings import Settings
    from contextipy.ui.windows.settings import SettingsWindow

    initial_settings = Settings(launch_on_startup=False, enable_notifications=True)

    load_settings = Mock(return_value=initial_settings)
    save_settings = Mock(return_value=(True, None))
    on_autostart_change = Mock(return_value=(True, None))

    window = SettingsWindow(
        load_settings=load_settings,
        save_settings=save_settings,
        on_autostart_change=on_autostart_change,
    )

    window._checkboxes["launch_on_startup"].setChecked(True)
    window._checkboxes["enable_notifications"].setChecked(False)

    window._show_success_dialog = Mock()

    window._on_save()

    on_autostart_change.assert_called_once_with(True)
    assert save_settings.call_count == 1
    saved_settings = save_settings.call_args[0][0]
    assert saved_settings.launch_on_startup is True
    assert saved_settings.enable_notifications is False

    window._show_success_dialog.assert_called_once()


def test_settings_window_autostart_failure(qapp):
    """Test handling of auto-start failure during save."""
    from contextipy.config.settings import Settings
    from contextipy.ui.windows.settings import SettingsWindow

    load_settings = Mock(return_value=Settings())
    save_settings = Mock(return_value=(True, None))
    on_autostart_change = Mock(return_value=(False, "Autostart error"))

    window = SettingsWindow(
        load_settings=load_settings,
        save_settings=save_settings,
        on_autostart_change=on_autostart_change,
    )

    window._checkboxes["launch_on_startup"].setChecked(True)

    window._show_error_dialog = Mock()

    window._on_save()

    on_autostart_change.assert_called_once_with(True)
    save_settings.assert_not_called()
    window._show_error_dialog.assert_called_once()


def test_settings_window_save_failure(qapp):
    """Test handling of save failure."""
    from contextipy.config.settings import Settings
    from contextipy.ui.windows.settings import SettingsWindow

    load_settings = Mock(return_value=Settings())
    save_settings = Mock(return_value=(False, "Save error"))
    on_autostart_change = Mock(return_value=(True, None))

    window = SettingsWindow(
        load_settings=load_settings,
        save_settings=save_settings,
        on_autostart_change=on_autostart_change,
    )

    window._checkboxes["launch_on_startup"].setChecked(True)

    window._show_error_dialog = Mock()

    window._on_save()

    on_autostart_change.assert_called_once_with(True)
    window._show_error_dialog.assert_called_once()


def test_settings_window_no_autostart_change(qapp):
    """Test saving settings when auto-start doesn't change."""
    from contextipy.config.settings import Settings
    from contextipy.ui.windows.settings import SettingsWindow

    initial_settings = Settings(launch_on_startup=True, enable_notifications=True)

    load_settings = Mock(return_value=initial_settings)
    save_settings = Mock(return_value=(True, None))
    on_autostart_change = Mock(return_value=(True, None))

    window = SettingsWindow(
        load_settings=load_settings,
        save_settings=save_settings,
        on_autostart_change=on_autostart_change,
    )

    window._show_success_dialog = Mock()

    window._on_save()

    on_autostart_change.assert_not_called()
    save_settings.assert_called_once()
    window._show_success_dialog.assert_called_once()


def test_settings_window_uses_settings_store(qapp, tmp_path):
    """Test that SettingsWindow can use a SettingsStore directly."""
    from contextipy.config.settings import Settings, SettingsStore
    from contextipy.ui.windows.settings import SettingsWindow

    settings_store = SettingsStore(path=tmp_path / "settings.json")
    initial_settings = Settings(launch_on_startup=True, enable_notifications=False)
    settings_store.save(initial_settings)

    on_autostart_change = Mock(return_value=(True, None))

    window = SettingsWindow(
        settings_store=settings_store,
        on_autostart_change=on_autostart_change,
    )

    assert window._checkboxes["launch_on_startup"].isChecked() is True
    assert window._checkboxes["enable_notifications"].isChecked() is False

    window._checkboxes["enable_notifications"].setChecked(True)

    window._show_success_dialog = Mock()

    window._on_save()

    loaded = settings_store.load()
    assert loaded.launch_on_startup is True
    assert loaded.enable_notifications is True


def test_settings_window_get_current_settings(qapp):
    """Test getting current settings from UI."""
    from contextipy.config.settings import Settings
    from contextipy.ui.windows.settings import SettingsWindow

    load_settings = Mock(return_value=Settings())

    window = SettingsWindow(load_settings=load_settings)

    window._checkboxes["launch_on_startup"].setChecked(True)
    window._checkboxes["enable_notifications"].setChecked(False)

    current_settings = window._get_current_settings()

    assert current_settings.launch_on_startup is True
    assert current_settings.enable_notifications is False


def test_settings_window_load_error(qapp):
    """Test handling of load error."""
    from contextipy.ui.windows.settings import SettingsWindow

    load_settings = Mock(side_effect=Exception("Load error"))

    window = SettingsWindow(load_settings=load_settings)

    assert window is not None


def test_settings_window_renders_with_defaults(qapp):
    """Test that SettingsWindow renders with default settings."""
    from contextipy.ui.windows.settings import SettingsWindow

    window = SettingsWindow()

    assert window is not None
    assert window.windowTitle() == "Настройки"
    assert window._checkboxes["launch_on_startup"].isChecked() is False
    assert window._checkboxes["enable_notifications"].isChecked() is True
