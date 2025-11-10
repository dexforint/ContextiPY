"""Unit tests for the service manager module."""

import multiprocessing as mp
import queue
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest

from contextipy.execution.service_manager import (
    DefaultServiceEventHook,
    ServiceEventHook,
    ServiceInfo,
    ServiceManager,
    ServiceRequest,
    ServiceResponse,
    ServiceState,
    ServiceWorkerTarget,
    create_service_manager,
)


class TestServiceState:
    """Tests for ServiceState enum."""

    def test_states_exist(self) -> None:
        assert ServiceState.STOPPED.value == "stopped"
        assert ServiceState.STARTING.value == "starting"
        assert ServiceState.RUNNING.value == "running"
        assert ServiceState.STOPPING.value == "stopping"
        assert ServiceState.FAILED.value == "failed"


class TestServiceInfo:
    """Tests for ServiceInfo dataclass."""

    def test_create_basic(self) -> None:
        info = ServiceInfo(service_id="test_service", state=ServiceState.STOPPED)
        assert info.service_id == "test_service"
        assert info.state == ServiceState.STOPPED
        assert info.process is None
        assert info.started_at is None

    def test_with_process(self) -> None:
        mock_process = Mock()
        info = ServiceInfo(
            service_id="test_service",
            state=ServiceState.RUNNING,
            process=mock_process,
            started_at=time.time(),
        )
        assert info.process is mock_process
        assert info.started_at is not None


class TestServiceRequest:
    """Tests for ServiceRequest dataclass."""

    def test_create_basic(self) -> None:
        request = ServiceRequest(request_id="req-123", action="test_action")
        assert request.request_id == "req-123"
        assert request.action == "test_action"
        assert request.parameters == {}

    def test_with_parameters(self) -> None:
        request = ServiceRequest(
            request_id="req-123",
            action="test_action",
            parameters={"key": "value"},
        )
        assert request.parameters == {"key": "value"}


class TestServiceResponse:
    """Tests for ServiceResponse dataclass."""

    def test_success_response(self) -> None:
        response = ServiceResponse(request_id="req-123", success=True, result="test result")
        assert response.request_id == "req-123"
        assert response.success is True
        assert response.result == "test result"
        assert response.error is None

    def test_error_response(self) -> None:
        response = ServiceResponse(
            request_id="req-123",
            success=False,
            error="test error",
        )
        assert response.success is False
        assert response.error == "test error"


class TestDefaultServiceEventHook:
    """Tests for DefaultServiceEventHook."""

    def test_on_service_start(self) -> None:
        hook = DefaultServiceEventHook()
        hook.on_service_start("test_service")

    def test_on_service_running(self) -> None:
        hook = DefaultServiceEventHook()
        hook.on_service_running("test_service")

    def test_on_service_stop(self) -> None:
        hook = DefaultServiceEventHook()
        hook.on_service_stop("test_service")

    def test_on_service_error(self) -> None:
        hook = DefaultServiceEventHook()
        hook.on_service_error("test_service", "test error")
        hook.on_service_error("test_service", Exception("test exception"))


class TestServiceWorkerTarget:
    """Tests for ServiceWorkerTarget."""

    def test_init(self) -> None:
        factory = Mock()
        request_queue = mp.Queue()
        response_queue = mp.Queue()
        
        worker = ServiceWorkerTarget(
            "test_service",
            factory,
            request_queue,
            response_queue,
        )
        
        assert worker.service_id == "test_service"
        assert worker.service_factory is factory
        assert worker.request_queue is request_queue
        assert worker.response_queue is response_queue


class TestServiceManager:
    """Tests for ServiceManager."""

    def test_init_with_defaults(self) -> None:
        manager = ServiceManager()
        assert manager._max_downtime == 5.0
        assert manager._default_timeout == 30.0
        assert len(manager._services) == 0

    def test_init_with_custom_values(self) -> None:
        manager = ServiceManager(max_downtime=10.0, default_timeout=60.0)
        assert manager._max_downtime == 10.0
        assert manager._default_timeout == 60.0

    def test_init_with_event_hook(self) -> None:
        mock_hook = Mock(spec=ServiceEventHook)
        manager = ServiceManager(event_hook=mock_hook)
        assert manager._event_hook is mock_hook

    def test_register_service(self) -> None:
        manager = ServiceManager()
        factory = Mock()
        
        manager.register_service("test_service", factory)
        
        assert "test_service" in manager._services
        assert "test_service" in manager._service_factories
        assert manager._services["test_service"].service_id == "test_service"
        assert manager._services["test_service"].state == ServiceState.STOPPED

    def test_register_duplicate_service_raises_error(self) -> None:
        manager = ServiceManager()
        factory = Mock()
        
        manager.register_service("test_service", factory)
        
        with pytest.raises(ValueError, match="already registered"):
            manager.register_service("test_service", factory)

    def test_start_service_not_registered(self) -> None:
        manager = ServiceManager()
        
        with pytest.raises(ValueError, match="not registered"):
            manager.start_service("unknown_service")

    @patch("contextipy.execution.service_manager.mp.Process")
    def test_start_service_success(self, mock_process_class: MagicMock) -> None:
        mock_process = Mock()
        mock_process.is_alive.return_value = True
        mock_process_class.return_value = mock_process
        
        manager = ServiceManager()
        factory = Mock()
        manager.register_service("test_service", factory)
        
        result = manager.start_service("test_service")
        
        assert result is True
        assert manager._services["test_service"].state == ServiceState.RUNNING
        assert manager._services["test_service"].process is mock_process
        mock_process.start.assert_called_once()

    @patch("contextipy.execution.service_manager.mp.Process")
    def test_start_service_already_running(self, mock_process_class: MagicMock) -> None:
        mock_process = Mock()
        mock_process.is_alive.return_value = True
        mock_process_class.return_value = mock_process
        
        manager = ServiceManager()
        factory = Mock()
        manager.register_service("test_service", factory)
        
        manager.start_service("test_service")
        result = manager.start_service("test_service")
        
        assert result is True
        assert mock_process.start.call_count == 1

    def test_stop_service_not_registered(self) -> None:
        manager = ServiceManager()
        
        with pytest.raises(ValueError, match="not registered"):
            manager.stop_service("unknown_service")

    def test_stop_service_already_stopped(self) -> None:
        manager = ServiceManager()
        factory = Mock()
        manager.register_service("test_service", factory)
        
        result = manager.stop_service("test_service")
        
        assert result is True
        assert manager._services["test_service"].state == ServiceState.STOPPED

    @patch("contextipy.execution.service_manager.mp.Process")
    def test_stop_service_success(self, mock_process_class: MagicMock) -> None:
        mock_process = Mock()
        mock_process.is_alive.return_value = True
        mock_process_class.return_value = mock_process
        
        manager = ServiceManager()
        factory = Mock()
        manager.register_service("test_service", factory)
        manager.start_service("test_service")
        
        mock_process.is_alive.return_value = False
        result = manager.stop_service("test_service")
        
        assert result is True
        assert manager._services["test_service"].state == ServiceState.STOPPED

    def test_is_service_running_not_registered(self) -> None:
        manager = ServiceManager()
        assert manager.is_service_running("unknown_service") is False

    def test_is_service_running_stopped(self) -> None:
        manager = ServiceManager()
        factory = Mock()
        manager.register_service("test_service", factory)
        
        assert manager.is_service_running("test_service") is False

    @patch("contextipy.execution.service_manager.mp.Process")
    def test_is_service_running_running(self, mock_process_class: MagicMock) -> None:
        mock_process = Mock()
        mock_process.is_alive.return_value = True
        mock_process_class.return_value = mock_process
        
        manager = ServiceManager()
        factory = Mock()
        manager.register_service("test_service", factory)
        manager.start_service("test_service")
        
        assert manager.is_service_running("test_service") is True

    @patch("contextipy.execution.service_manager.mp.Process")
    def test_ensure_service_running_starts_if_stopped(
        self, mock_process_class: MagicMock
    ) -> None:
        mock_process = Mock()
        mock_process.is_alive.return_value = True
        mock_process_class.return_value = mock_process
        
        manager = ServiceManager()
        factory = Mock()
        manager.register_service("test_service", factory)
        
        result = manager.ensure_service_running("test_service")
        
        assert result is True
        assert manager._services["test_service"].state == ServiceState.RUNNING

    @patch("contextipy.execution.service_manager.mp.Process")
    def test_ensure_service_running_already_running(
        self, mock_process_class: MagicMock
    ) -> None:
        mock_process = Mock()
        mock_process.is_alive.return_value = True
        mock_process_class.return_value = mock_process
        
        manager = ServiceManager()
        factory = Mock()
        manager.register_service("test_service", factory)
        manager.start_service("test_service")
        
        result = manager.ensure_service_running("test_service")
        
        assert result is True
        assert mock_process.start.call_count == 1

    def test_get_service_state_not_registered(self) -> None:
        manager = ServiceManager()
        
        with pytest.raises(ValueError, match="not registered"):
            manager.get_service_state("unknown_service")

    def test_get_service_state(self) -> None:
        manager = ServiceManager()
        factory = Mock()
        manager.register_service("test_service", factory)
        
        state = manager.get_service_state("test_service")
        
        assert state == ServiceState.STOPPED

    def test_dispatch_success(self) -> None:
        manager = ServiceManager()
        factory = Mock()
        manager.register_service("test_service", factory)
        
        request = ServiceRequest(request_id="req-1", action="do_work")
        response = ServiceResponse(request_id="req-1", success=True, result="ok")
        
        request_queue = Mock()
        response_queue = Mock()
        response_queue.get.return_value = response
        
        manager._request_queues["test_service"] = request_queue
        manager._response_queues["test_service"] = response_queue
        
        with patch.object(manager, "ensure_service_running", return_value=True) as ensure_mock:
            result = manager.dispatch("test_service", request, timeout=2.0)
        
        ensure_mock.assert_called_once_with("test_service")
        request_queue.put.assert_called_once_with(request)
        response_queue.get.assert_called_once()
        assert result is response

    def test_dispatch_timeout(self) -> None:
        manager = ServiceManager()
        factory = Mock()
        manager.register_service("test_service", factory)
        
        request = ServiceRequest(request_id="req-1", action="do_work")
        
        request_queue = Mock()
        response_queue = Mock()
        response_queue.get.side_effect = queue.Empty
        
        manager._request_queues["test_service"] = request_queue
        manager._response_queues["test_service"] = response_queue
        
        with patch.object(manager, "ensure_service_running", return_value=True):
            with pytest.raises(TimeoutError):
                manager.dispatch("test_service", request, timeout=0.1)
        
        request_queue.put.assert_called_once_with(request)
        response_queue.get.assert_called_once()

    def test_dispatch_not_registered(self) -> None:
        manager = ServiceManager()
        request = ServiceRequest(request_id="req-1", action="do_work")
        
        with pytest.raises(ValueError, match="not registered"):
            manager.dispatch("unknown_service", request)

    def test_dispatch_start_failure(self) -> None:
        manager = ServiceManager()
        factory = Mock()
        manager.register_service("test_service", factory)
        
        request_queue = Mock()
        response_queue = Mock()
        manager._request_queues["test_service"] = request_queue
        manager._response_queues["test_service"] = response_queue
        request = ServiceRequest(request_id="req-1", action="do_work")
        
        with patch.object(manager, "ensure_service_running", return_value=False):
            with pytest.raises(RuntimeError, match="Failed to start"):
                manager.dispatch("test_service", request)

    @patch("contextipy.execution.service_manager.mp.Process")
    def test_shutdown(self, mock_process_class: MagicMock) -> None:
        mock_process = Mock()
        mock_process.is_alive.return_value = True
        mock_process_class.return_value = mock_process
        
        manager = ServiceManager()
        factory = Mock()
        manager.register_service("test_service", factory)
        manager.start_service("test_service")
        
        mock_process.is_alive.return_value = False
        manager.shutdown()
        
        assert manager._services["test_service"].state == ServiceState.STOPPED

    def test_event_hooks_called(self) -> None:
        mock_hook = Mock(spec=ServiceEventHook)
        manager = ServiceManager(event_hook=mock_hook)
        factory = Mock()
        manager.register_service("test_service", factory)
        
        with patch("contextipy.execution.service_manager.mp.Process") as mock_process_class:
            mock_process = Mock()
            mock_process.is_alive.return_value = True
            mock_process_class.return_value = mock_process
            
            manager.start_service("test_service")
            
            mock_hook.on_service_start.assert_called_once_with("test_service")
            mock_hook.on_service_running.assert_called_once_with("test_service")


class TestCreateServiceManager:
    """Tests for create_service_manager factory function."""

    def test_creates_manager(self) -> None:
        manager = create_service_manager()
        assert isinstance(manager, ServiceManager)

    def test_passes_event_hook(self) -> None:
        mock_hook = Mock(spec=ServiceEventHook)
        manager = create_service_manager(event_hook=mock_hook)
        assert manager._event_hook is mock_hook

    def test_passes_max_downtime(self) -> None:
        manager = create_service_manager(max_downtime=15.0)
        assert manager._max_downtime == 15.0
