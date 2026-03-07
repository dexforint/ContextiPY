from __future__ import annotations

import inspect
import sys
import time
import traceback
from pathlib import Path
from typing import Any

from pcontext.registrar.introspection import import_module_from_path
from pcontext.runner.bindings import build_callable_kwargs, resolve_object_by_qualname
from pcontext.runner.service_models import (
    SERVICE_REQUEST_ADAPTER,
    ServiceErrorResponse,
    ServiceInvokeRequest,
    ServiceInvokeSuccessResponse,
    ServicePingRequest,
    ServicePongResponse,
    ServiceRequest,
    ServiceShutdownRequest,
    ServiceShutdownResponse,
    ServiceStartRequest,
    ServiceStartedResponse,
)
from pcontext.runtime.action_codec import serialize_action_result


class ServiceRuntime:
    """
    Долгоживущий рантайм одного сервиса.

    Внутри одного процесса живёт ровно один экземпляр пользовательского сервиса.
    """

    def __init__(self) -> None:
        self._service_instance: object | None = None
        self._service_class: type[object] | None = None

    def _cleanup_instance(self) -> None:
        """
        Пытается корректно освободить ресурсы сервиса.

        Сначала ищем явный `shutdown()`, потом `close()`.
        Если этих методов нет, просто удаляем ссылку на экземпляр.
        """
        if self._service_instance is None:
            return

        instance = self._service_instance
        self._service_instance = None
        self._service_class = None

        for method_name in ("shutdown", "close"):
            method = getattr(instance, method_name, None)
            if callable(method):
                method()
                break

    def start(self, request: ServiceStartRequest) -> ServiceStartedResponse:
        """
        Импортирует модуль, создаёт экземпляр сервиса и сохраняет его в памяти.
        """
        if self._service_instance is not None:
            raise RuntimeError("Сервис уже запущен внутри этого service-host процесса.")

        source_file = Path(request.source_file).expanduser().resolve()
        scripts_root = Path(request.scripts_root).expanduser().resolve()

        module = import_module_from_path(
            source_file,
            scripts_root=scripts_root,
        )
        service_class = resolve_object_by_qualname(module, request.service_qualname)

        if not inspect.isclass(service_class):
            raise TypeError("Целевой объект сервиса не является классом.")

        if service_class.__init__ is object.__init__:
            kwargs: dict[str, Any] = {}
        else:
            kwargs = build_callable_kwargs(
                service_class.__init__,
                context=None,
                parameter_values=request.parameter_values,
                skip_self=True,
            )

        started_at = time.perf_counter()
        instance = service_class(**kwargs)
        duration_ms = int((time.perf_counter() - started_at) * 1000)

        self._service_class = service_class
        self._service_instance = instance

        return ServiceStartedResponse(duration_ms=duration_ms)

    def invoke(self, request: ServiceInvokeRequest) -> ServiceInvokeSuccessResponse:
        """
        Вызывает метод уже запущенного сервиса.
        """
        if self._service_instance is None or self._service_class is None:
            raise RuntimeError("Сервис ещё не был запущен.")

        if not hasattr(self._service_class, request.method_name):
            raise AttributeError(f"У сервиса нет метода '{request.method_name}'.")

        unbound_method = getattr(self._service_class, request.method_name)
        bound_method = getattr(self._service_instance, request.method_name)

        if not callable(bound_method):
            raise TypeError(f"Атрибут '{request.method_name}' не является вызываемым.")

        if inspect.iscoroutinefunction(unbound_method):
            raise TypeError("Асинхронные методы сервиса пока не поддерживаются.")

        kwargs = build_callable_kwargs(
            unbound_method,
            context=request.context,
            parameter_values=request.parameter_values,
            skip_self=True,
        )

        started_at = time.perf_counter()
        result = bound_method(**kwargs)
        duration_ms = int((time.perf_counter() - started_at) * 1000)

        return ServiceInvokeSuccessResponse(
            action=serialize_action_result(result),
            duration_ms=duration_ms,
        )

    def shutdown(self) -> ServiceShutdownResponse:
        """
        Корректно останавливает сервис.
        """
        self._cleanup_instance()
        return ServiceShutdownResponse()


def _make_error_response(error: BaseException, *, phase: str) -> ServiceErrorResponse:
    """
    Преобразует Python-ошибку в структурированный JSON-ответ.
    """
    return ServiceErrorResponse(
        phase=phase,  # type: ignore[arg-type]
        error_type=type(error).__name__,
        message=str(error),
        traceback=traceback.format_exc(),
    )


def _handle_request(runtime: ServiceRuntime, request: ServiceRequest):
    """
    Маршрутизирует входящий service-host запрос.
    """
    if isinstance(request, ServicePingRequest):
        return ServicePongResponse()

    if isinstance(request, ServiceStartRequest):
        return runtime.start(request)

    if isinstance(request, ServiceInvokeRequest):
        return runtime.invoke(request)

    if isinstance(request, ServiceShutdownRequest):
        return runtime.shutdown()

    raise RuntimeError("Получен неподдерживаемый тип service-host запроса.")


def main() -> int:
    """
    Точка входа service-host процесса.

    Протокол очень простой:
    - service manager пишет одну JSON-строку в stdin;
    - service host отвечает одной JSON-строкой в stdout.
    """
    runtime = ServiceRuntime()

    try:
        for raw_line in sys.stdin:
            if not raw_line.strip():
                continue

            phase = "protocol"
            parsed_request: ServiceRequest | None = None

            try:
                parsed_request = SERVICE_REQUEST_ADAPTER.validate_json(raw_line)

                if isinstance(parsed_request, ServiceStartRequest):
                    phase = "start"
                elif isinstance(parsed_request, ServiceInvokeRequest):
                    phase = "invoke"
                elif isinstance(parsed_request, ServiceShutdownRequest):
                    phase = "shutdown"

                response = _handle_request(runtime, parsed_request)
            except Exception as error:  # noqa: BLE001
                response = _make_error_response(error, phase=phase)

            print(response.model_dump_json(), flush=True)

            if isinstance(parsed_request, ServiceShutdownRequest):
                break

    finally:
        try:
            runtime._cleanup_instance()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
