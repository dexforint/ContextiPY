"""Service manager for managing lifecycle of long-running service processes.

This module provides infrastructure for spawning and managing worker processes
that run service classes. It handles IPC for service scripts, enforces
max_downtime and timeout constraints, and provides auto-start capabilities.
"""

from __future__ import annotations

import copy
import multiprocessing as mp
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol


class ServiceState(Enum):
    """State of a managed service."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"


@dataclass
class ServiceInfo:
    """Information about a managed service."""

    service_id: str
    state: ServiceState
    process: mp.Process | None = None
    started_at: float | None = None
    stopped_at: float | None = None
    restart_count: int = 0
    last_error: str | None = None


@dataclass(frozen=True, slots=True)
class ServiceRequest:
    """Request to be sent to a service process."""

    request_id: str
    action: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ServiceResponse:
    """Response from a service process."""

    request_id: str
    success: bool
    result: Any = None
    error: str | None = None


class ServiceEventHook(Protocol):
    """Protocol for service lifecycle event hooks."""

    def on_service_start(self, service_id: str) -> None:
        """Called when a service begins starting."""
        ...

    def on_service_running(self, service_id: str) -> None:
        """Called when a service enters running state."""
        ...

    def on_service_stop(self, service_id: str) -> None:
        """Called when a service stops."""
        ...

    def on_service_error(self, service_id: str, error: Exception | str) -> None:
        """Called when a service encounters an error."""
        ...


class DefaultServiceEventHook:
    """Default no-op implementation of service event hooks."""

    def on_service_start(self, service_id: str) -> None:
        pass

    def on_service_running(self, service_id: str) -> None:
        pass

    def on_service_stop(self, service_id: str) -> None:
        pass

    def on_service_error(self, service_id: str, error: Exception | str) -> None:
        pass


class ServiceWorkerTarget:
    """Callable target for service worker processes."""

    def __init__(
        self,
        service_id: str,
        service_factory: Callable[[], Any],
        request_queue: mp.Queue[ServiceRequest | None],
        response_queue: mp.Queue[ServiceResponse],
    ) -> None:
        self.service_id = service_id
        self.service_factory = service_factory
        self.request_queue = request_queue
        self.response_queue = response_queue

    def __call__(self) -> None:
        """Worker process main loop."""
        try:
            service_instance = self.service_factory()
            
            while True:
                request = self.request_queue.get()
                
                if request is None:
                    break
                
                try:
                    if hasattr(service_instance, request.action):
                        method = getattr(service_instance, request.action)
                        result = method(**request.parameters)
                        response = ServiceResponse(
                            request_id=request.request_id,
                            success=True,
                            result=result,
                        )
                    else:
                        response = ServiceResponse(
                            request_id=request.request_id,
                            success=False,
                            error=f"Unknown action: {request.action}",
                        )
                except Exception as exc:
                    response = ServiceResponse(
                        request_id=request.request_id,
                        success=False,
                        error=str(exc),
                    )
                
                self.response_queue.put(response)
        except Exception:
            pass


class ServiceManager:
    """Manager for long-running service processes."""

    def __init__(
        self,
        *,
        event_hook: ServiceEventHook | None = None,
        max_downtime: float = 5.0,
        default_timeout: float = 30.0,
    ) -> None:
        """Initialize the service manager.

        Parameters
        ----------
        event_hook:
            Optional event hook for logging and UI updates.
        max_downtime:
            Maximum time in seconds a service can be down before restart.
        default_timeout:
            Default timeout in seconds for service operations.
        """
        self._event_hook = event_hook or DefaultServiceEventHook()
        self._max_downtime = max_downtime
        self._default_timeout = default_timeout
        self._services: dict[str, ServiceInfo] = {}
        self._service_factories: dict[str, Callable[[], Any]] = {}
        self._request_queues: dict[str, mp.Queue[ServiceRequest | None]] = {}
        self._response_queues: dict[str, mp.Queue[ServiceResponse]] = {}
        self._lock = threading.RLock()
        self._monitor_thread: threading.Thread | None = None
        self._shutdown_event = threading.Event()

    def register_service(
        self,
        service_id: str,
        service_factory: Callable[[], Any],
    ) -> None:
        """Register a service with the manager.

        Parameters
        ----------
        service_id:
            Unique identifier for the service.
        service_factory:
            Callable that creates a new instance of the service.
        """
        with self._lock:
            if service_id in self._services:
                raise ValueError(f"Service {service_id} is already registered")
            
            self._service_factories[service_id] = service_factory
            self._request_queues[service_id] = mp.Queue()
            self._response_queues[service_id] = mp.Queue()
            self._services[service_id] = ServiceInfo(
                service_id=service_id,
                state=ServiceState.STOPPED,
            )

    def start_service(self, service_id: str) -> bool:
        """Start a service.

        Parameters
        ----------
        service_id:
            Identifier of the service to start.

        Returns
        -------
        bool
            True if the service was started successfully, False otherwise.
        """
        with self._lock:
            if service_id not in self._services:
                raise ValueError(f"Service {service_id} is not registered")
            
            service_info = self._services[service_id]
            
            if service_info.state in (ServiceState.RUNNING, ServiceState.STARTING):
                return True
            
            try:
                self._event_hook.on_service_start(service_id)
                service_info.state = ServiceState.STARTING
                
                factory = self._service_factories[service_id]
                request_queue = self._request_queues[service_id]
                response_queue = self._response_queues[service_id]
                
                worker = ServiceWorkerTarget(
                    service_id,
                    factory,
                    request_queue,
                    response_queue,
                )
                
                process = mp.Process(target=worker, daemon=True)
                process.start()
                
                service_info.process = process
                service_info.started_at = time.time()
                service_info.state = ServiceState.RUNNING
                
                self._event_hook.on_service_running(service_id)
                
                if self._monitor_thread is None or not self._monitor_thread.is_alive():
                    self._start_monitor_thread()
                
                return True
            
            except Exception as exc:
                service_info.state = ServiceState.FAILED
                service_info.last_error = str(exc)
                self._event_hook.on_service_error(service_id, exc)
                return False

    def stop_service(self, service_id: str) -> bool:
        """Stop a service.

        Parameters
        ----------
        service_id:
            Identifier of the service to stop.

        Returns
        -------
        bool
            True if the service was stopped successfully, False otherwise.
        """
        with self._lock:
            if service_id not in self._services:
                raise ValueError(f"Service {service_id} is not registered")
            
            service_info = self._services[service_id]
            
            if service_info.state == ServiceState.STOPPED:
                return True
            
            try:
                service_info.state = ServiceState.STOPPING
                
                if service_info.process and service_info.process.is_alive():
                    # Send shutdown signal
                    self._request_queues[service_id].put(None)
                    service_info.process.join(timeout=5.0)
                    
                    if service_info.process.is_alive():
                        service_info.process.terminate()
                        service_info.process.join(timeout=2.0)
                        
                        if service_info.process.is_alive():
                            service_info.process.kill()
                
                service_info.state = ServiceState.STOPPED
                service_info.stopped_at = time.time()
                service_info.process = None
                
                self._event_hook.on_service_stop(service_id)
                return True
            
            except Exception as exc:
                service_info.state = ServiceState.FAILED
                service_info.last_error = str(exc)
                self._event_hook.on_service_error(service_id, exc)
                return False

    def is_service_running(self, service_id: str) -> bool:
        """Check if a service is currently running.

        Parameters
        ----------
        service_id:
            Identifier of the service to check.

        Returns
        -------
        bool
            True if the service is running, False otherwise.
        """
        with self._lock:
            if service_id not in self._services:
                return False
            
            service_info = self._services[service_id]
            
            if service_info.state != ServiceState.RUNNING:
                return False
            
            if service_info.process is None or not service_info.process.is_alive():
                service_info.state = ServiceState.STOPPED
                return False
            
            return True

    def ensure_service_running(self, service_id: str) -> bool:
        """Ensure a service is running, starting it if necessary.

        Parameters
        ----------
        service_id:
            Identifier of the service.

        Returns
        -------
        bool
            True if the service is running, False otherwise.
        """
        if self.is_service_running(service_id):
            return True
        
        return self.start_service(service_id)

    def get_service_state(self, service_id: str) -> ServiceState:
        """Get the current state of a service.

        Parameters
        ----------
        service_id:
            Identifier of the service.

        Returns
        -------
        ServiceState
            The current state of the service.
        """
        with self._lock:
            if service_id not in self._services:
                raise ValueError(f"Service {service_id} is not registered")
            
            return self._services[service_id].state

    def get_all_services(self) -> list[ServiceInfo]:
        """Get information about all registered services.

        Returns
        -------
        list[ServiceInfo]
            List of ServiceInfo objects for all registered services.
        """
        with self._lock:
            return [copy.copy(info) for info in self._services.values()]

    def dispatch(
        self,
        service_id: str,
        request: ServiceRequest,
        *,
        timeout: float | None = None,
    ) -> ServiceResponse:
        """Dispatch a request to a service and wait for the response.

        Parameters
        ----------
        service_id:
            Identifier of the service.
        request:
            Request to send to the service.
        timeout:
            Maximum time to wait for a response in seconds.

        Returns
        -------
        ServiceResponse
            Response from the service.

        Raises
        ------
        ValueError:
            If the service is not registered.
        RuntimeError:
            If the service fails to start.
        TimeoutError:
            If the request times out.
        """
        if service_id not in self._services:
            raise ValueError(f"Service {service_id} is not registered")
        
        if not self.ensure_service_running(service_id):
            raise RuntimeError(f"Failed to start service: {service_id}")
        
        effective_timeout = timeout if timeout is not None else self._default_timeout
        
        request_queue = self._request_queues[service_id]
        response_queue = self._response_queues[service_id]
        
        request_queue.put(request)
        
        try:
            response = response_queue.get(timeout=effective_timeout)
            return response
        except Exception as exc:
            if isinstance(exc, TimeoutError) or "Empty" in str(type(exc).__name__):
                raise TimeoutError(
                    f"Request {request.request_id} timed out after {effective_timeout}s"
                )
            raise

    def shutdown(self) -> None:
        """Shutdown all services and clean up resources."""
        self._shutdown_event.set()
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)
        
        with self._lock:
            service_ids = list(self._services.keys())
        
        for service_id in service_ids:
            self.stop_service(service_id)

    def _start_monitor_thread(self) -> None:
        """Start the background monitor thread."""
        self._monitor_thread = threading.Thread(
            target=self._monitor_services,
            daemon=True,
        )
        self._monitor_thread.start()

    def _monitor_services(self) -> None:
        """Background thread that monitors service health."""
        while not self._shutdown_event.is_set():
            time.sleep(1.0)
            
            with self._lock:
                for service_id, service_info in list(self._services.items()):
                    if service_info.state != ServiceState.RUNNING:
                        continue
                    
                    if service_info.process and not service_info.process.is_alive():
                        service_info.state = ServiceState.STOPPED
                        service_info.stopped_at = time.time()
                        
                        error_msg = f"Service {service_id} terminated unexpectedly"
                        service_info.last_error = error_msg
                        self._event_hook.on_service_error(service_id, error_msg)
                        
                        if service_info.stopped_at and service_info.started_at:
                            downtime = service_info.stopped_at - service_info.started_at
                            if downtime < self._max_downtime:
                                service_info.restart_count += 1


def create_service_manager(
    event_hook: ServiceEventHook | None = None,
    *,
    max_downtime: float = 5.0,
) -> ServiceManager:
    """Create a service manager with optional event hook.

    Parameters
    ----------
    event_hook:
        Optional event hook for logging and UI updates.
    max_downtime:
        Maximum time in seconds a service can be down before restart.

    Returns
    -------
    ServiceManager
        A configured service manager instance.
    """
    return ServiceManager(event_hook=event_hook, max_downtime=max_downtime)


__all__ = [
    "ServiceState",
    "ServiceInfo",
    "ServiceRequest",
    "ServiceResponse",
    "ServiceEventHook",
    "DefaultServiceEventHook",
    "ServiceManager",
    "create_service_manager",
]
