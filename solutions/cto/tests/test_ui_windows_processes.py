"""Tests for processes status window."""

from __future__ import annotations

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
def processes_fixture():
    """Create fixture with simulated process data."""
    from contextipy.ui.windows.processes import ProcessInfo

    from types import SimpleNamespace

    mock_result = SimpleNamespace(success=True, error_message=None)

    return [
        ProcessInfo(
            process_id="process-1",
            script_id="script-A",
            started_at=1234567890.0,
            is_running=True,
            result=None,
        ),
        ProcessInfo(
            process_id="process-2",
            script_id="script-B",
            started_at=1234567890.0,
            is_running=False,
            result=mock_result,
        ),
    ]


def test_processes_window_renders_list(qapp, processes_fixture):
    """Test that ProcessesWindow renders list of processes."""
    from contextipy.ui.windows.processes import ProcessesWindow

    get_processes_mock = Mock(return_value=processes_fixture)
    stop_process_mock = Mock(return_value=(True, None))

    window = ProcessesWindow(
        get_processes=get_processes_mock,
        stop_process=stop_process_mock,
        refresh_interval=5000,
    )

    assert window is not None
    assert window.windowTitle() == "Процессы"

    get_processes_mock.assert_called()

    model = window._model
    assert len(model.processes) == len(processes_fixture)
    assert model.processes[0].process_id == "process-1"


def test_processes_window_empty_list(qapp):
    """Test that ProcessesWindow renders empty state."""
    from contextipy.ui.windows.processes import ProcessesWindow

    get_processes_mock = Mock(return_value=[])
    stop_process_mock = Mock(return_value=(True, None))

    window = ProcessesWindow(
        get_processes=get_processes_mock,
        stop_process=stop_process_mock,
    )

    assert window is not None
    get_processes_mock.assert_called()

    model = window._model
    assert len(model.processes) == 0


def test_processes_window_stop_button_dispatches_callback(qapp, processes_fixture):
    """Test that stop button dispatches callback for running process."""
    from contextipy.ui.windows.processes import ProcessesWindow

    get_processes_mock = Mock(return_value=processes_fixture)
    stop_process_mock = Mock(return_value=(True, None))

    window = ProcessesWindow(
        get_processes=get_processes_mock,
        stop_process=stop_process_mock,
    )

    window._on_stop_process("process-1")

    stop_process_mock.assert_called_once_with("process-1")


def test_processes_window_stop_failure_shows_error(qapp, processes_fixture):
    """Test that stop failure shows error dialog."""
    from contextipy.ui.windows.processes import ProcessesWindow

    get_processes_mock = Mock(return_value=processes_fixture)
    stop_process_mock = Mock(return_value=(False, "Test error message"))

    window = ProcessesWindow(
        get_processes=get_processes_mock,
        stop_process=stop_process_mock,
    )

    window._show_error_dialog = Mock()

    window._on_stop_process("process-1")

    stop_process_mock.assert_called_once_with("process-1")
    window._show_error_dialog.assert_called_once()


def test_processes_window_model_update(processes_fixture):
    """Test that ProcessModel can update processes."""
    from contextipy.ui.windows.processes import ProcessModel

    model = ProcessModel()
    assert len(model.processes) == 0

    model.update_processes(processes_fixture)
    assert len(model.processes) == 2
    assert model.processes[0].process_id == "process-1"


def test_processes_window_refresh_timer_stops_on_close(qapp, processes_fixture):
    """Test that refresh timer stops when window closes."""
    from contextipy.ui.windows.processes import ProcessesWindow

    get_processes_mock = Mock(return_value=processes_fixture)
    stop_process_mock = Mock(return_value=(True, None))

    window = ProcessesWindow(
        get_processes=get_processes_mock,
        stop_process=stop_process_mock,
    )

    timer = window._refresh_timer
    assert timer.isActive()

    window.close()
    assert not timer.isActive()
