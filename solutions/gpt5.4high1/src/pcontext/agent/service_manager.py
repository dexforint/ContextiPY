from __future__ import annotations

import json
import logging
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
from typing import TextIO

from pcontext.registrar.models import ServiceManifest, ServiceScriptManifest
from pcontext.runner.service_models import (
    SERVICE_RESPONSE_ADAPTER,
    ServiceErrorResponse,
    ServiceInvokeRequest,
    ServiceInvokeSuccessResponse,
    ServicePingRequest,
    ServicePongResponse,
    ServiceResponse,
    ServiceShutdownRequest,
    ServiceShutdownResponse,
    ServiceStartRequest,
    ServiceStartedResponse,
)
from pcontext.runtime.ipc_models import ShellContext
from pcontext.storage.state import StateStore


LOGGER = logging.getLogger(__name__)
_DEFAULT_START_TIMEOUT_SECONDS = 60.0
_DEFAULT_INVOKE_TIMEOUT_SECONDS = 60.0
_DEFAULT_SHUTDOWN_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True, slots=True)
class ServiceControlResult:
    """
    Результат команды запуска или остановки сервиса.
    """

    accepted: bool
    running: bool
    message: str


@dataclass(frozen=True, slots=True)
class ServiceStatusView:
    """
    Состояние сервиса для UI и IPC.
    """

    service_id: str
    title: str
    running: bool
    on_startup: bool
    script_count: int


@dataclass(frozen=True, slots=True)
class ServiceInvocationFailure:
    """
    Ошибка вызова метода сервиса.
    """

    error_type: str
    message: str
    traceback: str


@dataclass(frozen=True, slots=True)
class _ServiceProcessHandle:
    """
    Живой process-handle одного сервиса.
    """

    service_id: str
    manifest: ServiceManifest
    process: subprocess.Popen[str]
    io_lock: threading.Lock


def _manifest_signature(manifest: ServiceManifest) -> str:
    """
    Возвращает стабильный отпечаток манифеста.
    """
    payload = manifest.model_dump(mode="json")
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _read_line_with_timeout(pipe: TextIO, timeout_seconds: float) -> str:
    """
    Читает одну строку из pipe с таймаутом.
    """
    result_queue: Queue[str | BaseException] = Queue(maxsize=1)

    def reader() -> None:
        try:
            result_queue.put(pipe.readline())
        except BaseException as error:  # noqa: BLE001
            result_queue.put(error)

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()

    try:
        result = result_queue.get(timeout=timeout_seconds)
    except Empty as error:
        raise TimeoutError(
            f"Истёк таймаут ожидания ответа от service-host: {timeout_seconds} сек."
        ) from error

    if isinstance(result, BaseException):
        raise result

    return result


class ServiceManager:
    """
    Управляет долгоживущими service-host процессами.
    """

    def __init__(self, scripts_root: Path, state_store: StateStore) -> None:
        self._scripts_root = scripts_root.expanduser().resolve()
        self._state_store = state_store
        self._lock = threading.RLock()
        self._manifests: dict[str, ServiceManifest] = {}
        self._processes: dict[str, _ServiceProcessHandle] = {}

    def _spawn_process(
        self, service_id: str, manifest: ServiceManifest
    ) -> _ServiceProcessHandle:
        """
        Запускает новый service-host процесс.
        """
        process = subprocess.Popen(
            [sys.executable, "-m", "pcontext.runner.service_worker"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )

        return _ServiceProcessHandle(
            service_id=service_id,
            manifest=manifest,
            process=process,
            io_lock=threading.Lock(),
        )

    def _read_stderr_if_exited(self, process: subprocess.Popen[str]) -> str:
        """
        Возвращает stderr, если процесс уже завершился.
        """
        if process.poll() is None:
            return ""

        stderr = process.stderr
        if stderr is None:
            return ""

        return stderr.read().strip()

    def _send_request(
        self,
        handle: _ServiceProcessHandle,
        request: object,
        *,
        timeout_seconds: float,
    ) -> ServiceResponse:
        """
        Отправляет один JSON-запрос service-host процессу и ждёт один JSON-ответ.
        """
        process = handle.process

        if process.poll() is not None:
            stderr_text = self._read_stderr_if_exited(process)
            raise RuntimeError(
                f"Service-host процесс уже завершён. stderr: {stderr_text or '<пусто>'}"
            )

        stdin = process.stdin
        stdout = process.stdout

        if stdin is None or stdout is None:
            raise RuntimeError("У service-host процесса недоступны stdin/stdout pipe.")

        payload = request.model_dump_json()

        with handle.io_lock:
            stdin.write(payload)
            stdin.write("\n")
            stdin.flush()

            raw_response = _read_line_with_timeout(stdout, timeout_seconds)

        if not raw_response:
            stderr_text = self._read_stderr_if_exited(process)
            raise RuntimeError(
                f"Service-host не вернул ответ. stderr: {stderr_text or '<пусто>'}"
            )

        return SERVICE_RESPONSE_ADAPTER.validate_json(raw_response)

    def _force_stop_process(self, handle: _ServiceProcessHandle) -> None:
        """
        Принудительно завершает service-host процесс.
        """
        process = handle.process

        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=_DEFAULT_SHUTDOWN_TIMEOUT_SECONDS)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=_DEFAULT_SHUTDOWN_TIMEOUT_SECONDS)
        finally:
            for pipe in (process.stdin, process.stdout, process.stderr):
                if pipe is not None:
                    try:
                        pipe.close()
                    except Exception:
                        pass

    def _is_running_locked(self, service_id: str) -> bool:
        """
        Проверяет, что сервис действительно ещё жив.
        """
        handle = self._processes.get(service_id)
        if handle is None:
            return False

        if handle.process.poll() is not None:
            LOGGER.warning("Service-host '%s' завершился неожиданно.", service_id)
            self._processes.pop(service_id, None)
            self._force_stop_process(handle)
            return False

        return True

    def is_running(self, service_id: str) -> bool:
        """
        Возвращает текущее состояние сервиса.
        """
        with self._lock:
            return self._is_running_locked(service_id)

    def _start_service_locked(self, service_id: str) -> ServiceControlResult:
        """
        Запускает сервис под уже взятым lock.
        """
        manifest = self._manifests.get(service_id)
        if manifest is None:
            return ServiceControlResult(
                accepted=False,
                running=False,
                message=f"Сервис '{service_id}' не зарегистрирован.",
            )

        if self._is_running_locked(service_id):
            return ServiceControlResult(
                accepted=True,
                running=True,
                message=f"Сервис '{manifest.title}' уже запущен.",
            )

        handle = self._spawn_process(service_id, manifest)
        init_parameter_values = self._state_store.get_parameter_values(service_id)

        try:
            start_response = self._send_request(
                handle,
                ServiceStartRequest(
                    scripts_root=str(self._scripts_root),
                    source_file=manifest.source_file,
                    service_qualname=manifest.qualname,
                    parameter_values=init_parameter_values,
                ),
                timeout_seconds=_DEFAULT_START_TIMEOUT_SECONDS,
            )
        except Exception as error:  # noqa: BLE001
            self._force_stop_process(handle)
            return ServiceControlResult(
                accepted=False,
                running=False,
                message=f"Не удалось запустить сервис '{manifest.title}': {error}",
            )

        if isinstance(start_response, ServiceErrorResponse):
            self._force_stop_process(handle)
            return ServiceControlResult(
                accepted=False,
                running=False,
                message=(
                    f"Ошибка запуска сервиса '{manifest.title}': "
                    f"{start_response.error_type}: {start_response.message}"
                ),
            )

        if not isinstance(start_response, ServiceStartedResponse):
            self._force_stop_process(handle)
            return ServiceControlResult(
                accepted=False,
                running=False,
                message="Service-host вернул неожиданный ответ при запуске сервиса.",
            )

        try:
            ping_response = self._send_request(
                handle,
                ServicePingRequest(),
                timeout_seconds=5.0,
            )
        except Exception as error:  # noqa: BLE001
            self._force_stop_process(handle)
            return ServiceControlResult(
                accepted=False,
                running=False,
                message=f"Сервис '{manifest.title}' запустился, но не ответил на ping: {error}",
            )

        if not isinstance(ping_response, ServicePongResponse):
            self._force_stop_process(handle)
            return ServiceControlResult(
                accepted=False,
                running=False,
                message="Service-host не подтвердил свою готовность после запуска.",
            )

        self._processes[service_id] = handle

        return ServiceControlResult(
            accepted=True,
            running=True,
            message=f"Сервис '{manifest.title}' запущен за {start_response.duration_ms} мс.",
        )

    def start_service(self, service_id: str) -> ServiceControlResult:
        """
        Публичный запуск сервиса.
        """
        with self._lock:
            return self._start_service_locked(service_id)

    def _stop_service_locked(self, service_id: str) -> ServiceControlResult:
        """
        Останавливает сервис под уже взятым lock.
        """
        handle = self._processes.pop(service_id, None)
        manifest = self._manifests.get(service_id)

        if handle is None:
            title = manifest.title if manifest is not None else service_id
            return ServiceControlResult(
                accepted=True,
                running=False,
                message=f"Сервис '{title}' уже остановлен.",
            )

        try:
            response = self._send_request(
                handle,
                ServiceShutdownRequest(),
                timeout_seconds=_DEFAULT_SHUTDOWN_TIMEOUT_SECONDS,
            )
            if isinstance(response, ServiceErrorResponse):
                message = (
                    f"Сервис '{handle.manifest.title}' остановлен принудительно после ошибки: "
                    f"{response.error_type}: {response.message}"
                )
            elif isinstance(response, ServiceShutdownResponse):
                message = f"Сервис '{handle.manifest.title}' корректно остановлен."
            else:
                message = f"Сервис '{handle.manifest.title}' вернул неожиданный ответ при остановке."
        except Exception as error:  # noqa: BLE001
            message = (
                f"Сервис '{handle.manifest.title}' остановлен принудительно: {error}"
            )
        finally:
            self._force_stop_process(handle)

        return ServiceControlResult(
            accepted=True,
            running=False,
            message=message,
        )

    def stop_service(self, service_id: str) -> ServiceControlResult:
        """
        Публичная остановка сервиса.
        """
        with self._lock:
            return self._stop_service_locked(service_id)

    def close(self) -> None:
        """
        Останавливает все запущенные сервисы.
        """
        with self._lock:
            for service_id in list(self._processes):
                self._stop_service_locked(service_id)

    def set_manifests(self, manifests: tuple[ServiceManifest, ...]) -> list[str]:
        """
        Обновляет список известных сервисов.
        """
        new_manifests = {manifest.id: manifest for manifest in manifests}
        startup_messages: list[str] = []

        with self._lock:
            for service_id, handle in list(self._processes.items()):
                new_manifest = new_manifests.get(service_id)
                if new_manifest is None:
                    self._stop_service_locked(service_id)
                    continue

                if _manifest_signature(handle.manifest) != _manifest_signature(
                    new_manifest
                ):
                    self._stop_service_locked(service_id)

            self._manifests = new_manifests

            for manifest in self._manifests.values():
                if not manifest.on_startup:
                    continue

                result = self._start_service_locked(manifest.id)
                if not result.accepted:
                    startup_messages.append(result.message)

        return startup_messages

    def list_services(self) -> list[ServiceStatusView]:
        """
        Возвращает текущее состояние всех известных сервисов.
        """
        with self._lock:
            items = [
                ServiceStatusView(
                    service_id=manifest.id,
                    title=manifest.title,
                    running=self._is_running_locked(manifest.id),
                    on_startup=manifest.on_startup,
                    script_count=len(manifest.scripts),
                )
                for manifest in self._manifests.values()
            ]

        return sorted(items, key=lambda item: (item.title.lower(), item.service_id))

    def invoke_service_method(
        self,
        service_id: str,
        script_manifest: ServiceScriptManifest,
        context: ShellContext | None,
    ) -> ServiceInvokeSuccessResponse | ServiceInvocationFailure:
        """
        Вызывает метод уже запущенного сервиса.
        """
        with self._lock:
            if not self._is_running_locked(service_id):
                return ServiceInvocationFailure(
                    error_type="RuntimeError",
                    message=f"Сервис '{service_id}' сейчас не запущен.",
                    traceback="",
                )

            handle = self._processes[service_id]

        timeout_seconds = (
            float(script_manifest.timeout)
            if script_manifest.timeout is not None
            else _DEFAULT_INVOKE_TIMEOUT_SECONDS
        )

        method_parameter_values = self._state_store.get_parameter_values(
            script_manifest.id
        )

        try:
            response = self._send_request(
                handle,
                ServiceInvokeRequest(
                    method_name=script_manifest.method_name,
                    context=context,
                    parameter_values=method_parameter_values,
                ),
                timeout_seconds=timeout_seconds,
            )
        except Exception as error:  # noqa: BLE001
            with self._lock:
                self._processes.pop(service_id, None)
                self._force_stop_process(handle)

            return ServiceInvocationFailure(
                error_type=type(error).__name__,
                message=str(error),
                traceback="",
            )

        if isinstance(response, ServiceErrorResponse):
            return ServiceInvocationFailure(
                error_type=response.error_type,
                message=response.message,
                traceback=response.traceback,
            )

        if not isinstance(response, ServiceInvokeSuccessResponse):
            return ServiceInvocationFailure(
                error_type="RuntimeError",
                message="Service-host вернул неожиданный ответ при вызове метода сервиса.",
                traceback="",
            )

        return response
