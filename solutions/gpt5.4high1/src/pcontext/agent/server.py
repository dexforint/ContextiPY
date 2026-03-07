from __future__ import annotations

import logging
import os
import secrets
import socketserver
import threading
import time
from typing import cast

from pydantic import ValidationError

from pcontext.agent.registry import LiveRegistry
from pcontext.config import PContextPaths, ensure_directories
from pcontext.runtime.ask_runtime import request_user_answers
from pcontext.runtime.discovery import remove_agent_endpoint, write_agent_endpoint
from pcontext.runtime.ipc_models import (
    AgentEndpoint,
    ErrorResponse,
    InvokeMenuItemRequest,
    InvokeMenuItemResponse,
    ListServicesRequest,
    ListServicesResponse,
    PingRequest,
    PingResponse,
    QueryMenuRequest,
    QueryMenuResponse,
    REQUEST_ADAPTER,
    ReloadRegistryRequest,
    ReloadRegistryResponse,
    RequestMessage,
    ResponseMessage,
    ServiceDescriptor,
    StartServiceRequest,
    StartServiceResponse,
    StopServiceRequest,
    StopServiceResponse,
)
from pcontext.runtime.question_models import AskUserRequest, AskUserResponse
from pcontext.runtime.shell import normalize_shell_context
from pcontext.storage.state import StateStore


LOGGER = logging.getLogger(__name__)
_MAX_REQUEST_BYTES = 1_000_000


class AgentApplication:
    """
    Живое приложение-агент.
    """

    def __init__(self, token: str, paths: PContextPaths) -> None:
        self._token = token
        self._paths = paths
        self._state_store = StateStore(paths.state_db)
        self._registry = LiveRegistry(paths.scripts, self._state_store)
        self._log_catalog_state("Первичная загрузка")

    @property
    def registry(self) -> LiveRegistry:
        """
        Возвращает живой реестр скриптов и сервисов.
        """
        return self._registry

    @property
    def state_store(self) -> StateStore:
        """
        Возвращает SQLite-хранилище состояния.
        """
        return self._state_store

    def close(self) -> None:
        """
        Останавливает сервисы при завершении агента.
        """
        self._registry.close()

    def _authorize(self, token: str) -> bool:
        """
        Проверяет токен доступа.
        """
        return secrets.compare_digest(self._token, token)

    def _unauthorized_response(self) -> ErrorResponse:
        """
        Формирует стандартный ответ при неверном токене.
        """
        return ErrorResponse(
            error_code="unauthorized",
            message="Неверный токен доступа к агенту.",
        )

    def _log_catalog_state(self, reason: str) -> None:
        """
        Пишет в лог краткую сводку по текущему каталогу.
        """
        catalog = self._registry.catalog
        LOGGER.info(
            "%s: commands=%s, services=%s, failures=%s",
            reason,
            len(catalog.context_commands),
            len(catalog.services),
            len(catalog.failures),
        )

        for failure in catalog.failures:
            LOGGER.warning(
                "Ошибка регистрации: %s | %s", failure.source_file, failure.message
            )

        for message in self._registry.service_startup_messages:
            LOGGER.warning("Ошибка автозапуска сервиса: %s", message)

    def handle_request(self, request: RequestMessage) -> ResponseMessage:
        """
        Обрабатывает один входящий запрос.
        """
        if not self._authorize(request.token):
            return self._unauthorized_response()

        if isinstance(request, PingRequest):
            return PingResponse(pid=os.getpid())

        if isinstance(request, QueryMenuRequest):
            context = normalize_shell_context(request.context)
            items = self._registry.list_menu_items(context)
            return QueryMenuResponse(items=items)

        if isinstance(request, InvokeMenuItemRequest):
            context = normalize_shell_context(request.context)
            result = self._registry.invoke(request.menu_item_id, context)
            return InvokeMenuItemResponse(
                accepted=result.accepted,
                message=result.message,
            )

        if isinstance(request, ReloadRegistryRequest):
            result = self._registry.reload()
            self._log_catalog_state("Перезагрузка каталога")
            return ReloadRegistryResponse(
                command_count=result.command_count,
                service_count=result.service_count,
                failure_count=result.failure_count,
            )

        if isinstance(request, ListServicesRequest):
            services = [
                ServiceDescriptor(
                    service_id=item.service_id,
                    title=item.title,
                    running=item.running,
                    on_startup=item.on_startup,
                    script_count=item.script_count,
                )
                for item in self._registry.list_services()
            ]
            return ListServicesResponse(services=services)

        if isinstance(request, StartServiceRequest):
            result = self._registry.start_service(request.service_id)
            return StartServiceResponse(
                service_id=request.service_id,
                accepted=result.accepted,
                running=result.running,
                message=result.message,
            )

        if isinstance(request, StopServiceRequest):
            result = self._registry.stop_service(request.service_id)
            return StopServiceResponse(
                service_id=request.service_id,
                accepted=result.accepted,
                running=result.running,
                message=result.message,
            )

        if isinstance(request, AskUserRequest):
            answers = request_user_answers(request.form_schema)
            return AskUserResponse(
                cancelled=answers is None,
                answers={} if answers is None else answers,
            )

        return ErrorResponse(
            error_code="unsupported_request",
            message="Получен неподдерживаемый тип запроса.",
        )


class AgentTcpServer(socketserver.ThreadingTCPServer):
    """
    Многопоточный TCP-сервер для локального IPC.
    """

    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int], app: AgentApplication) -> None:
        self.app = app
        super().__init__(server_address, AgentRequestHandler)


class AgentRequestHandler(socketserver.StreamRequestHandler):
    """
    Обработчик одного TCP-соединения.
    """

    def handle(self) -> None:
        server = cast(AgentTcpServer, self.server)

        try:
            raw_request = self.rfile.readline(_MAX_REQUEST_BYTES)
            if not raw_request:
                return

            request = REQUEST_ADAPTER.validate_json(raw_request)
            response = server.app.handle_request(request)
        except ValidationError as error:
            response = ErrorResponse(
                error_code="invalid_request",
                message=str(error),
            )
        except Exception as error:  # noqa: BLE001
            LOGGER.exception("Необработанная ошибка при обработке IPC-запроса.")
            response = ErrorResponse(
                error_code="internal_error",
                message=str(error),
            )

        self.wfile.write(response.model_dump_json().encode("utf-8") + b"\n")
        self.wfile.flush()


class AgentRuntime:
    """
    Управляемый рантайм встроенного IPC-агента.
    """

    def __init__(self, paths: PContextPaths, *, host: str = "127.0.0.1") -> None:
        self._paths = paths
        self._host = host
        self._lock = threading.RLock()
        self._application: AgentApplication | None = None
        self._server: AgentTcpServer | None = None
        self._thread: threading.Thread | None = None
        self._endpoint: AgentEndpoint | None = None

    @property
    def application(self) -> AgentApplication:
        """
        Возвращает приложение-агент.
        """
        if self._application is None:
            raise RuntimeError("AgentRuntime ещё не был запущен.")
        return self._application

    @property
    def endpoint(self) -> AgentEndpoint:
        """
        Возвращает endpoint запущенного агента.
        """
        if self._endpoint is None:
            raise RuntimeError("AgentRuntime ещё не был запущен.")
        return self._endpoint

    def start(self) -> None:
        """
        Запускает встроенный IPC-агент в отдельном фоне.
        """
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return

            ensure_directories(self._paths)

            token = secrets.token_urlsafe(32)
            application = AgentApplication(token=token, paths=self._paths)
            server = AgentTcpServer((self._host, 0), application)

            address = server.server_address
            port = int(address[1])

            endpoint = AgentEndpoint(
                host=self._host,
                port=port,
                token=token,
                pid=os.getpid(),
            )

            write_agent_endpoint(self._paths.agent_endpoint, endpoint)

            thread = threading.Thread(
                target=server.serve_forever,
                kwargs={"poll_interval": 0.2},
                daemon=True,
                name="pcontext-agent-server",
            )
            thread.start()

            self._application = application
            self._server = server
            self._thread = thread
            self._endpoint = endpoint

            LOGGER.info("Агент запущен на %s:%s", self._host, port)
            LOGGER.info("Файл discovery: %s", self._paths.agent_endpoint)
            LOGGER.info("SQLite state DB: %s", self._paths.state_db)

    def stop(self) -> None:
        """
        Останавливает встроенный IPC-агент.
        """
        with self._lock:
            application = self._application
            server = self._server
            thread = self._thread

            self._application = None
            self._server = None
            self._thread = None
            self._endpoint = None

        try:
            if server is not None:
                server.shutdown()
                server.server_close()

            if thread is not None and thread.is_alive():
                thread.join(timeout=5.0)

            if application is not None:
                application.close()
        finally:
            remove_agent_endpoint(self._paths.agent_endpoint)
            LOGGER.info("Агент остановлен.")


def serve_agent(paths: PContextPaths, *, host: str = "127.0.0.1") -> None:
    """
    Запускает IPC-агент в foreground-режиме.
    """
    runtime = AgentRuntime(paths, host=host)
    runtime.start()

    try:
        while True:
            time.sleep(0.5)
    finally:
        runtime.stop()
