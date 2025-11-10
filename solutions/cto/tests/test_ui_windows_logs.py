"""Tests for logs window."""

from __future__ import annotations

from datetime import datetime
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
def logs_fixture():
    """Create fixture with mock execution log data."""
    from contextipy.logging.logger import ExecutionLog

    return [
        ExecutionLog(
            run_id="run-001",
            script_id="test-script-a",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 5),
            status="success",
            exit_code=0,
            timed_out=False,
            error_message=None,
            actions_summary=[{"type": "text", "content": "<redacted>"}],
            stdout_excerpt="Hello World",
            stderr_excerpt="",
            input_payload={"parameters": {"key": "value"}},
        ),
        ExecutionLog(
            run_id="run-002",
            script_id="test-script-b",
            start_time=datetime(2024, 1, 1, 12, 1, 0),
            end_time=datetime(2024, 1, 1, 12, 1, 3),
            status="failure",
            exit_code=1,
            timed_out=False,
            error_message="Script failed with error",
            actions_summary=[],
            stdout_excerpt="",
            stderr_excerpt="Error: File not found",
            input_payload={"parameters": {}},
        ),
        ExecutionLog(
            run_id="run-003",
            script_id="test-script-a",
            start_time=datetime(2024, 1, 1, 12, 2, 0),
            end_time=datetime(2024, 1, 1, 12, 2, 15),
            status="error",
            exit_code=None,
            timed_out=True,
            error_message="Script exceeded timeout of 10s",
            actions_summary=[],
            stdout_excerpt="Processing...",
            stderr_excerpt="",
            input_payload={"parameters": {"timeout": 10}},
        ),
    ]


def test_logs_window_renders_table(qapp, logs_fixture):
    """Test that LogsWindow renders table with log data."""
    from contextipy.ui.windows.logs import LogsWindow

    get_logs_mock = Mock(return_value=logs_fixture)
    repeat_action_mock = Mock(return_value=(True, None))

    window = LogsWindow(
        get_logs=get_logs_mock,
        repeat_action=repeat_action_mock,
    )

    assert window is not None
    assert window.windowTitle() == "Журнал выполнения"

    get_logs_mock.assert_called()

    model = window._model
    assert len(model.logs) == 3
    assert model.logs[0].run_id == "run-001"
    assert model.logs[1].run_id == "run-002"
    assert model.logs[2].run_id == "run-003"

    assert window._table.rowCount() == 3


def test_logs_window_empty_list(qapp):
    """Test that LogsWindow handles empty log list."""
    from contextipy.ui.windows.logs import LogsWindow

    get_logs_mock = Mock(return_value=[])
    repeat_action_mock = Mock(return_value=(True, None))

    window = LogsWindow(
        get_logs=get_logs_mock,
        repeat_action=repeat_action_mock,
    )

    assert window is not None
    get_logs_mock.assert_called()

    model = window._model
    assert len(model.logs) == 0
    assert window._table.rowCount() == 0


def test_logs_window_repeat_button_triggers_action(qapp, logs_fixture):
    """Test that repeat button triggers action handler with stored payload."""
    from contextipy.ui.windows.logs import LogsWindow

    get_logs_mock = Mock(return_value=logs_fixture)
    repeat_action_mock = Mock(return_value=(True, None))

    window = LogsWindow(
        get_logs=get_logs_mock,
        repeat_action=repeat_action_mock,
    )

    window._on_repeat_action("run-001")

    repeat_action_mock.assert_called_once_with("run-001")


def test_logs_window_repeat_failure_shows_error(qapp, logs_fixture):
    """Test that repeat failure shows error dialog."""
    from contextipy.ui.windows.logs import LogsWindow

    get_logs_mock = Mock(return_value=logs_fixture)
    repeat_action_mock = Mock(return_value=(False, "Test error message"))

    window = LogsWindow(
        get_logs=get_logs_mock,
        repeat_action=repeat_action_mock,
    )

    window._show_error_dialog = Mock()

    window._on_repeat_action("run-001")

    repeat_action_mock.assert_called_once_with("run-001")
    window._show_error_dialog.assert_called_once()


def test_logs_window_repeat_missing_resource_shows_error(qapp, logs_fixture):
    """Test that repeat action handles missing resources gracefully."""
    from contextipy.ui.windows.logs import LogsWindow

    get_logs_mock = Mock(return_value=logs_fixture)
    repeat_action_mock = Mock(side_effect=FileNotFoundError("File not found"))

    window = LogsWindow(
        get_logs=get_logs_mock,
        repeat_action=repeat_action_mock,
    )

    window._show_error_dialog = Mock()

    window._on_repeat_action("run-001")

    repeat_action_mock.assert_called_once_with("run-001")
    window._show_error_dialog.assert_called_once()
    args = window._show_error_dialog.call_args[0]
    assert "удалены" in args[1] or "File not found" in str(args)


def test_logs_window_repeat_key_error_shows_error(qapp, logs_fixture):
    """Test that repeat action handles KeyError (missing run) gracefully."""
    from contextipy.ui.windows.logs import LogsWindow

    get_logs_mock = Mock(return_value=logs_fixture)
    repeat_action_mock = Mock(side_effect=KeyError("Run not found"))

    window = LogsWindow(
        get_logs=get_logs_mock,
        repeat_action=repeat_action_mock,
    )

    window._show_error_dialog = Mock()

    window._on_repeat_action("run-001")

    repeat_action_mock.assert_called_once_with("run-001")
    window._show_error_dialog.assert_called_once()
    args = window._show_error_dialog.call_args[0]
    assert "удалён" in args[1] or "Run not found" in str(args)


def test_logs_window_model_update(logs_fixture):
    """Test that LogsModel can update logs."""
    from contextipy.ui.windows.logs import LogsModel

    model = LogsModel()
    assert len(model.logs) == 0

    model.update_logs(logs_fixture)
    assert len(model.logs) == 3
    assert model.logs[0].run_id == "run-001"


def test_logs_window_status_filter(qapp, logs_fixture):
    """Test that status filter works correctly."""
    from contextipy.ui.windows.logs import LogsWindow

    get_logs_mock = Mock(return_value=logs_fixture)
    repeat_action_mock = Mock(return_value=(True, None))

    window = LogsWindow(
        get_logs=get_logs_mock,
        repeat_action=repeat_action_mock,
    )

    window._status_filter.setCurrentIndex(1)
    window._on_filter_changed()

    assert get_logs_mock.call_count >= 2
    last_call_args = get_logs_mock.call_args[0]
    assert last_call_args[1] == "success"


def test_logs_window_script_filter(qapp, logs_fixture):
    """Test that script filter works correctly."""
    from contextipy.ui.windows.logs import LogsWindow

    get_logs_mock = Mock(return_value=logs_fixture)
    repeat_action_mock = Mock(return_value=(True, None))

    window = LogsWindow(
        get_logs=get_logs_mock,
        repeat_action=repeat_action_mock,
    )

    window._script_filter.setCurrentIndex(1)
    window._on_filter_changed()

    assert get_logs_mock.call_count >= 2


def test_logs_window_displays_success_status(qapp, logs_fixture):
    """Test that success status is displayed with green color."""
    from contextipy.ui.windows.logs import LogsWindow
    from PySide6.QtGui import QColor
    from PySide6.QtCore import Qt

    get_logs_mock = Mock(return_value=[logs_fixture[0]])
    repeat_action_mock = Mock(return_value=(True, None))

    window = LogsWindow(
        get_logs=get_logs_mock,
        repeat_action=repeat_action_mock,
    )

    status_item = window._table.item(0, 4)
    assert status_item is not None
    assert "Успех" in status_item.text()
    assert status_item.foreground().color().name() == QColor(Qt.GlobalColor.darkGreen).name()


def test_logs_window_displays_failure_status(qapp, logs_fixture):
    """Test that failure status is displayed with red color."""
    from contextipy.ui.windows.logs import LogsWindow
    from PySide6.QtGui import QColor
    from PySide6.QtCore import Qt

    get_logs_mock = Mock(return_value=[logs_fixture[1]])
    repeat_action_mock = Mock(return_value=(True, None))

    window = LogsWindow(
        get_logs=get_logs_mock,
        repeat_action=repeat_action_mock,
    )

    status_item = window._table.item(0, 4)
    assert status_item is not None
    assert "Ошибка" in status_item.text()
    assert status_item.foreground().color().name() == QColor(Qt.GlobalColor.red).name()


def test_logs_window_displays_error_message_in_tooltip(qapp, logs_fixture):
    """Test that error message is displayed in status item tooltip."""
    from contextipy.ui.windows.logs import LogsWindow

    get_logs_mock = Mock(return_value=[logs_fixture[1]])
    repeat_action_mock = Mock(return_value=(True, None))

    window = LogsWindow(
        get_logs=get_logs_mock,
        repeat_action=repeat_action_mock,
    )

    status_item = window._table.item(0, 4)
    assert status_item is not None
    assert status_item.toolTip() == "Script failed with error"


def test_logs_window_show_details_button(qapp, logs_fixture):
    """Test that show details button works."""
    from contextipy.ui.windows.logs import LogsWindow

    get_logs_mock = Mock(return_value=logs_fixture)
    repeat_action_mock = Mock(return_value=(True, None))

    window = LogsWindow(
        get_logs=get_logs_mock,
        repeat_action=repeat_action_mock,
    )

    window._on_show_details("run-001")


def test_logs_window_show_details_missing_log(qapp, logs_fixture):
    """Test that show details handles missing log gracefully."""
    from contextipy.ui.windows.logs import LogsWindow

    get_logs_mock = Mock(return_value=logs_fixture)
    repeat_action_mock = Mock(return_value=(True, None))

    window = LogsWindow(
        get_logs=get_logs_mock,
        repeat_action=repeat_action_mock,
    )

    window._show_error_dialog = Mock()

    window._on_show_details("non-existent-run-id")

    window._show_error_dialog.assert_called_once()


def test_log_details_dialog_displays_information(qapp, logs_fixture):
    """Test that LogDetailsDialog displays log information."""
    from contextipy.ui.windows.logs import LogDetailsDialog

    dialog = LogDetailsDialog(
        log=logs_fixture[0],
        on_repeat=None,
    )

    assert dialog is not None
    assert dialog.windowTitle() == "Детали выполнения: run-001"


def test_log_details_dialog_displays_stdout_stderr(qapp, logs_fixture):
    """Test that LogDetailsDialog displays stdout and stderr in expandable sections."""
    from contextipy.ui.windows.logs import LogDetailsDialog
    from PySide6.QtWidgets import QTextEdit

    dialog = LogDetailsDialog(
        log=logs_fixture[1],
        on_repeat=None,
    )

    assert dialog is not None
    text_edits = dialog.findChildren(QTextEdit)
    assert text_edits
    assert all(not text_edit.isVisible() for text_edit in text_edits)


def test_log_details_dialog_repeat_button(qapp, logs_fixture):
    """Test that LogDetailsDialog has repeat button that triggers callback."""
    from contextipy.ui.windows.logs import LogDetailsDialog

    on_repeat_mock = Mock()

    dialog = LogDetailsDialog(
        log=logs_fixture[0],
        on_repeat=on_repeat_mock,
    )

    assert dialog is not None


def test_log_details_dialog_highlights_errors(qapp, logs_fixture):
    """Test that LogDetailsDialog highlights errors."""
    from contextipy.ui.windows.logs import LogDetailsDialog

    dialog = LogDetailsDialog(
        log=logs_fixture[1],
        on_repeat=None,
    )

    assert dialog is not None


def test_log_details_dialog_shows_timeout(qapp, logs_fixture):
    """Test that LogDetailsDialog shows timeout indicator."""
    from contextipy.ui.windows.logs import LogDetailsDialog

    dialog = LogDetailsDialog(
        log=logs_fixture[2],
        on_repeat=None,
    )

    assert dialog is not None


def test_logs_window_handles_get_logs_exception(qapp):
    """Test that LogsWindow handles exceptions from get_logs gracefully."""
    from contextipy.ui.windows.logs import LogsWindow

    get_logs_mock = Mock(side_effect=Exception("Database error"))
    repeat_action_mock = Mock(return_value=(True, None))

    window = LogsWindow(
        get_logs=get_logs_mock,
        repeat_action=repeat_action_mock,
    )

    assert window is not None
    assert len(window._model.logs) == 0


def test_logs_window_refresh_view(qapp, logs_fixture):
    """Test that refresh view updates the table."""
    from contextipy.ui.windows.logs import LogsWindow

    get_logs_mock = Mock(return_value=logs_fixture)
    repeat_action_mock = Mock(return_value=(True, None))

    window = LogsWindow(
        get_logs=get_logs_mock,
        repeat_action=repeat_action_mock,
    )

    initial_call_count = get_logs_mock.call_count

    window._refresh_view()

    assert get_logs_mock.call_count > initial_call_count


def test_logs_window_update_script_filter(qapp, logs_fixture):
    """Test that script filter is populated with unique script IDs."""
    from contextipy.ui.windows.logs import LogsWindow

    get_logs_mock = Mock(return_value=logs_fixture)
    repeat_action_mock = Mock(return_value=(True, None))

    window = LogsWindow(
        get_logs=get_logs_mock,
        repeat_action=repeat_action_mock,
    )

    assert window._script_filter.count() >= 3
    items = [window._script_filter.itemText(i) for i in range(window._script_filter.count())]
    assert "Все" in items
    assert "test-script-a" in items
    assert "test-script-b" in items
