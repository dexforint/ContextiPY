"""Tests for services status window."""

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
def services_fixture():
    """Create fixture with simulated service data."""
    from contextipy.execution.service_manager import ServiceInfo, ServiceState

    return [
        ServiceInfo(
            service_id="test-service",
            state=ServiceState.RUNNING,
            started_at=1234567890.0,
            restart_count=0,
            last_error=None,
        ),
        ServiceInfo(
            service_id="test-service-2",
            state=ServiceState.STOPPED,
            started_at=None,
            restart_count=1,
            last_error="Test error",
        ),
    ]


def test_services_window_renders_list(qapp, services_fixture):
    """Test that ServicesWindow renders list of services."""
    from contextipy.ui.windows.services import ServicesWindow

    get_services_mock = Mock(return_value=services_fixture)
    stop_service_mock = Mock(return_value=(True, None))

    window = ServicesWindow(
        get_services=get_services_mock,
        stop_service=stop_service_mock,
        refresh_interval=5000,
    )

    assert window is not None
    assert window.windowTitle() == "Запущенные сервисы"

    get_services_mock.assert_called()

    model = window._model
    assert len(model.services) == 1
    assert model.services[0].service_id == "test-service"


def test_services_window_empty_list(qapp):
    """Test that ServicesWindow renders empty state."""
    from contextipy.ui.windows.services import ServicesWindow

    get_services_mock = Mock(return_value=[])
    stop_service_mock = Mock(return_value=(True, None))

    window = ServicesWindow(
        get_services=get_services_mock,
        stop_service=stop_service_mock,
    )

    assert window is not None
    get_services_mock.assert_called()

    model = window._model
    assert len(model.services) == 0


def test_services_window_stop_button_dispatches_callback(qapp, services_fixture):
    """Test that stop button dispatches callback."""
    from contextipy.ui.windows.services import ServicesWindow

    get_services_mock = Mock(return_value=services_fixture)
    stop_service_mock = Mock(return_value=(True, None))

    window = ServicesWindow(
        get_services=get_services_mock,
        stop_service=stop_service_mock,
    )

    window._on_stop_service("test-service")

    stop_service_mock.assert_called_once_with("test-service")


def test_services_window_stop_failure_shows_error(qapp, services_fixture):
    """Test that stop failure shows error dialog."""
    from contextipy.ui.windows.services import ServicesWindow

    get_services_mock = Mock(return_value=services_fixture)
    stop_service_mock = Mock(return_value=(False, "Test error message"))

    window = ServicesWindow(
        get_services=get_services_mock,
        stop_service=stop_service_mock,
    )

    window._show_error_dialog = Mock()

    window._on_stop_service("test-service")

    stop_service_mock.assert_called_once_with("test-service")
    window._show_error_dialog.assert_called_once()


def test_services_window_model_update(services_fixture):
    """Test that ServiceModel can update services."""
    from contextipy.ui.windows.services import ServiceModel

    model = ServiceModel()
    assert len(model.services) == 0

    model.update_services(services_fixture)
    assert len(model.services) == 2
    assert model.services[0].service_id == "test-service"


def test_services_window_refresh_timer_stops_on_close(qapp, services_fixture):
    """Test that refresh timer stops when window closes."""
    from contextipy.ui.windows.services import ServicesWindow

    get_services_mock = Mock(return_value=services_fixture)
    stop_service_mock = Mock(return_value=(True, None))

    window = ServicesWindow(
        get_services=get_services_mock,
        stop_service=stop_service_mock,
    )

    timer = window._refresh_timer
    assert timer.isActive()

    window.close()
    assert not timer.isActive()
