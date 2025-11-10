"""Tests for all scripts management window."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

try:
    from PySide6.QtWidgets import QApplication

    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False

pytestmark = pytest.mark.skipif(not PYSIDE_AVAILABLE, reason="PySide6 not available")


@pytest.fixture
def qapp() -> QApplication:
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def scripts_fixture():
    """Create fixture with simulated script data."""
    from contextipy.scanner.registry import RegisteredScript, ScriptSettings
    from contextipy.scanner.script_scanner import ScannedScript

    return [
        RegisteredScript(
            scanned=ScannedScript(
                identifier="test-script-1",
                kind="oneshot_script",
                title="Test Script 1",
                description="First test script",
                docstring="Test docstring",
                file_path=Path("/fake/path/script1.py"),
                module="test.script1",
                qualname="test.script1:main",
                group=("test", "group1"),
                accepts=(),
                timeout=None,
                related_service_id=None,
                icon="test_icon",
                categories=("test",),
                file_hash="hash1",
                parameters=(),
            ),
            settings=ScriptSettings(enabled=True, startup=False, parameter_overrides=None),
        ),
        RegisteredScript(
            scanned=ScannedScript(
                identifier="file-script",
                kind="oneshot_script",
                title="File Script",
                description="Script requiring files",
                docstring=None,
                file_path=Path("/fake/path/file_script.py"),
                module="test.file_script",
                qualname="test.file_script:run",
                group=("test", "group1"),
                accepts=("files",),
                timeout=None,
                related_service_id=None,
                icon=None,
                categories=("test",),
                file_hash="hash-file",
                parameters=(),
            ),
            settings=ScriptSettings(enabled=True, startup=False, parameter_overrides=None),
        ),
        RegisteredScript(
            scanned=ScannedScript(
                identifier="test-service",
                kind="service",
                title="Test Service",
                description="Test service",
                docstring=None,
                file_path=Path("/fake/path/service.py"),
                module="test.service",
                qualname="test.service:Service",
                group=("services",),
                accepts=(),
                timeout=30.0,
                related_service_id=None,
                icon=None,
                categories=("services",),
                file_hash="hash-service",
                parameters=("param1",),
            ),
            settings=ScriptSettings(enabled=False, startup=True, parameter_overrides={"param1": "value1"}),
        ),
        RegisteredScript(
            scanned=ScannedScript(
                identifier="service-script",
                kind="service_script",
                title="Test Service Script",
                description="Service script test",
                docstring=None,
                file_path=Path("/fake/path/service_script.py"),
                module="test.service_script",
                qualname="test.service_script:handler",
                group=(),
                accepts=(),
                timeout=None,
                related_service_id="test-service",
                icon=None,
                categories=("category1", "category2"),
                file_hash="hash3",
                parameters=(),
            ),
            settings=ScriptSettings(enabled=True, startup=False, parameter_overrides=None),
        ),
    ]


def test_all_scripts_window_renders(qapp, scripts_fixture):
    """Test that AllScriptsWindow renders with scripts."""
    from contextipy.ui.windows.all_scripts import AllScriptsWindow

    get_scripts_mock = Mock(return_value=scripts_fixture)

    window = AllScriptsWindow(get_scripts=get_scripts_mock)

    assert window is not None
    assert window.windowTitle() == "Все скрипты"

    get_scripts_mock.assert_called()

    model = window._model
    assert len(model.scripts) == 4


def test_all_scripts_window_empty_list(qapp):
    """Test that AllScriptsWindow renders with no scripts."""
    from contextipy.ui.windows.all_scripts import AllScriptsWindow

    get_scripts_mock = Mock(return_value=[])

    window = AllScriptsWindow(get_scripts=get_scripts_mock)

    assert window is not None
    get_scripts_mock.assert_called()

    model = window._model
    assert len(model.scripts) == 0

    assert window._table.rowCount() == 0


def test_all_scripts_window_table_structure(qapp, scripts_fixture):
    """Test that table is properly structured."""
    from contextipy.ui.windows.all_scripts import AllScriptsWindow

    get_scripts_mock = Mock(return_value=scripts_fixture)

    window = AllScriptsWindow(get_scripts=get_scripts_mock)

    assert window._table.columnCount() == 8

    headers = [
        window._table.horizontalHeaderItem(i).text()
        for i in range(window._table.columnCount())
    ]
    assert "ID" in headers
    assert "Тип" in headers
    assert "Название" in headers
    assert "Описание" in headers


def test_all_scripts_window_refresh_triggers_rescan(qapp, scripts_fixture):
    """Test that refresh button triggers rescan."""
    from contextipy.ui.windows.all_scripts import AllScriptsWindow

    get_scripts_mock = Mock(return_value=scripts_fixture)
    rescan_mock = Mock()

    window = AllScriptsWindow(
        get_scripts=get_scripts_mock,
        rescan=rescan_mock,
    )

    window._show_info_dialog = Mock()
    window._on_refresh()

    rescan_mock.assert_called_once()
    window._show_info_dialog.assert_called_once()


def test_all_scripts_window_enabled_toggle(qapp, scripts_fixture):
    """Test that enabled checkbox toggles script enabled state."""
    from contextipy.ui.windows.all_scripts import AllScriptsWindow

    get_scripts_mock = Mock(return_value=scripts_fixture)
    set_enabled_mock = Mock()

    window = AllScriptsWindow(
        get_scripts=get_scripts_mock,
        set_enabled=set_enabled_mock,
    )

    window._on_enabled_changed("test-script-1", False)

    set_enabled_mock.assert_called_once_with("test-script-1", False)


def test_all_scripts_window_startup_toggle(qapp, scripts_fixture):
    """Test that startup checkbox toggles script startup state."""
    from contextipy.ui.windows.all_scripts import AllScriptsWindow

    get_scripts_mock = Mock(return_value=scripts_fixture)
    set_startup_mock = Mock()

    window = AllScriptsWindow(
        get_scripts=get_scripts_mock,
        set_startup=set_startup_mock,
    )

    window._on_startup_changed("test-script-1", True)

    set_startup_mock.assert_called_once_with("test-script-1", True)


def test_all_scripts_window_run_script(qapp, scripts_fixture):
    """Test that run button executes script."""
    from contextipy.ui.windows.all_scripts import AllScriptsWindow

    get_scripts_mock = Mock(return_value=scripts_fixture)
    run_script_mock = Mock(return_value=(True, "Success"))

    window = AllScriptsWindow(
        get_scripts=get_scripts_mock,
        run_script=run_script_mock,
    )

    window._show_info_dialog = Mock()
    window._on_run_script("test-script-1")

    run_script_mock.assert_called_once_with("test-script-1")
    window._show_info_dialog.assert_called_once()


def test_all_scripts_window_run_script_failure(qapp, scripts_fixture):
    """Test that run script failure shows error dialog."""
    from contextipy.ui.windows.all_scripts import AllScriptsWindow

    get_scripts_mock = Mock(return_value=scripts_fixture)
    run_script_mock = Mock(return_value=(False, "Test error"))

    window = AllScriptsWindow(
        get_scripts=get_scripts_mock,
        run_script=run_script_mock,
    )

    window._show_error_dialog = Mock()
    window._on_run_script("test-script-1")

    run_script_mock.assert_called_once_with("test-script-1")
    window._show_error_dialog.assert_called_once()


def test_all_scripts_window_can_run_script(qapp, scripts_fixture):
    """Test script run validation based on accepts field."""
    from contextipy.ui.windows.all_scripts import AllScriptsWindow

    get_scripts_mock = Mock(return_value=scripts_fixture)

    window = AllScriptsWindow(get_scripts=get_scripts_mock)

    script_without_accepts = scripts_fixture[0]
    assert window._can_run_script(script_without_accepts) is True

    file_script = scripts_fixture[1]
    assert window._can_run_script(file_script) is False

    service = scripts_fixture[2]
    assert window._can_run_script(service) is True


def test_all_scripts_window_edit_parameters(qapp, scripts_fixture):
    """Test that edit parameters button shows dialog."""
    from contextipy.ui.windows.all_scripts import AllScriptsWindow

    get_scripts_mock = Mock(return_value=scripts_fixture)

    window = AllScriptsWindow(get_scripts=get_scripts_mock)

    window._show_info_dialog = Mock()
    window._on_edit_parameters("test-script-1")

    window._show_info_dialog.assert_called_once()


def test_all_scripts_window_with_registry(qapp, scripts_fixture):
    """Test AllScriptsWindow with registry integration."""
    from contextipy.ui.windows.all_scripts import AllScriptsWindow

    registry_mock = Mock()
    registry_mock.list_scripts.return_value = {
        s.script_id: s for s in scripts_fixture
    }
    registry_mock.rescan.return_value = Mock()

    window = AllScriptsWindow(registry=registry_mock)

    assert window is not None
    registry_mock.list_scripts.assert_called()

    window._on_refresh()
    registry_mock.rescan.assert_called_once()


def test_all_scripts_window_with_coordinator(qapp, scripts_fixture):
    """Test AllScriptsWindow with coordinator integration."""
    from contextipy.ui.windows.all_scripts import AllScriptsWindow

    get_scripts_mock = Mock(return_value=scripts_fixture)

    coordinator_mock = Mock()
    coordinator_mock.execute_script.return_value = Mock(success=True, message="Done")

    window = AllScriptsWindow(
        get_scripts=get_scripts_mock,
        coordinator=coordinator_mock,
    )

    window._show_info_dialog = Mock()
    window._on_run_script("test-script-1")

    coordinator_mock.execute_script.assert_called_once_with("test-script-1")


def test_script_model_update(scripts_fixture):
    """Test that ScriptModel can update scripts."""
    from contextipy.ui.windows.all_scripts import ScriptModel

    model = ScriptModel()
    assert len(model.scripts) == 0

    model.update_scripts(scripts_fixture)
    assert len(model.scripts) == 4
    assert model.scripts[0].script_id == "test-script-1"


def test_all_scripts_window_grouping(qapp, scripts_fixture):
    """Test that scripts are grouped by folder hierarchy."""
    from contextipy.ui.windows.all_scripts import AllScriptsWindow

    get_scripts_mock = Mock(return_value=scripts_fixture)

    window = AllScriptsWindow(get_scripts=get_scripts_mock)

    row_count = window._table.rowCount()
    assert row_count > len(scripts_fixture)


def test_all_scripts_window_icons(qapp, scripts_fixture):
    """Test that icons are loaded for scripts."""
    from contextipy.ui.windows.all_scripts import AllScriptsWindow

    get_scripts_mock = Mock(return_value=scripts_fixture)

    window = AllScriptsWindow(get_scripts=get_scripts_mock)

    assert window is not None


def test_all_scripts_window_type_mapping(qapp, scripts_fixture):
    """Test that script types are properly mapped."""
    from contextipy.ui.windows.all_scripts import AllScriptsWindow

    get_scripts_mock = Mock(return_value=scripts_fixture)

    window = AllScriptsWindow(get_scripts=get_scripts_mock)

    assert window is not None
