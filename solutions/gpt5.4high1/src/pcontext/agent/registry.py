from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

from pcontext.agent.catalog import AgentCatalog, load_agent_catalog
from pcontext.agent.service_manager import (
    ServiceControlResult,
    ServiceInvocationFailure,
    ServiceManager,
    ServiceStatusView,
)
from pcontext.registrar.models import OneshotScriptManifest, ServiceScriptManifest
from pcontext.runner.models import ExecutionErrorResponse, OneshotExecutionRequest
from pcontext.runner.subprocess_runner import execute_oneshot_in_subprocess
from pcontext.runtime.action_codec import describe_serialized_action
from pcontext.runtime.action_executor import execute_serialized_action
from pcontext.runtime.ipc_models import ShellContext, ShellEntry
from pcontext.runtime.matching import (
    build_visible_menu_items_from_manifest_commands,
    matches_manifest_input_rules,
)
from pcontext.runtime.shell import InvocationContext
from pcontext.storage.state import StateStore


@dataclass(frozen=True, slots=True)
class MenuInvocationResult:
    """
    Результат попытки выполнить пункт меню.
    """

    accepted: bool
    message: str


@dataclass(frozen=True, slots=True)
class RegistryReloadResult:
    """
    Сводка после перезагрузки каталога.
    """

    command_count: int
    service_count: int
    failure_count: int


class LiveRegistry:
    """
    Живой реестр зарегистрированных скриптов и сервисов.
    """

    def __init__(
        self,
        scripts_root: Path,
        state_store: StateStore | None = None,
    ) -> None:
        self._lock = threading.RLock()
        self._scripts_root = scripts_root.expanduser().resolve()
        self._state_store = (
            state_store
            if state_store is not None
            else StateStore(self._scripts_root.parent / "state.db")
        )
        self._service_manager = ServiceManager(self._scripts_root, self._state_store)
        self._catalog = load_agent_catalog(self._scripts_root)
        self._service_startup_messages = tuple(
            self._service_manager.set_manifests(self._catalog.services)
        )

    @property
    def catalog(self) -> AgentCatalog:
        """
        Возвращает текущий снимок каталога.
        """
        with self._lock:
            return self._catalog

    @property
    def service_startup_messages(self) -> tuple[str, ...]:
        """
        Возвращает сообщения об ошибках автозапуска сервисов.
        """
        with self._lock:
            return self._service_startup_messages

    def close(self) -> None:
        """
        Останавливает все сервисы при завершении агента.
        """
        with self._lock:
            self._service_manager.close()

    def reload(self) -> RegistryReloadResult:
        """
        Полностью пересканирует папку scripts и заменяет текущий каталог.
        """
        with self._lock:
            self._catalog = load_agent_catalog(self._scripts_root)
            self._service_startup_messages = tuple(
                self._service_manager.set_manifests(self._catalog.services)
            )

            return RegistryReloadResult(
                command_count=len(self._catalog.context_commands),
                service_count=len(self._catalog.services),
                failure_count=len(self._catalog.failures),
            )

    def list_services(self) -> list[ServiceStatusView]:
        """
        Возвращает текущее состояние сервисов.
        """
        return self._service_manager.list_services()

    def start_service(self, service_id: str) -> ServiceControlResult:
        """
        Реально запускает сервис.
        """
        return self._service_manager.start_service(service_id)

    def stop_service(self, service_id: str) -> ServiceControlResult:
        """
        Реально останавливает сервис.
        """
        return self._service_manager.stop_service(service_id)

    def list_menu_items(self, context: InvocationContext) -> list[object]:
        """
        Возвращает список видимых пунктов меню для конкретного shell-контекста.
        """
        with self._lock:
            commands = self._catalog.context_commands

        return build_visible_menu_items_from_manifest_commands(
            commands,
            context,
            is_service_running=self._service_manager.is_running,
        )

    def _find_oneshot_script(self, menu_item_id: str) -> OneshotScriptManifest | None:
        """
        Ищет oneshot-скрипт по идентификатору пункта меню.
        """
        with self._lock:
            return next(
                (
                    item
                    for item in self._catalog.oneshot_scripts
                    if item.id == menu_item_id
                ),
                None,
            )

    def _find_service_script(
        self, menu_item_id: str
    ) -> tuple[str, ServiceScriptManifest] | None:
        """
        Ищет метод сервиса по идентификатору.
        """
        with self._lock:
            for service in self._catalog.services:
                for script in service.scripts:
                    if script.id == menu_item_id:
                        return service.id, script

        return None

    def _to_shell_context(
        self, context: InvocationContext | None
    ) -> ShellContext | None:
        """
        Преобразует внутренний InvocationContext обратно в IPC-модель.
        """
        if context is None:
            return None

        return ShellContext(
            source=context.source,
            current_folder=(
                str(context.current_folder)
                if context.current_folder is not None
                else None
            ),
            entries=[
                ShellEntry(
                    path=str(entry.path),
                    entry_type=entry.entry_type,
                )
                for entry in context.entries
            ],
        )

    def _add_run_log(
        self,
        *,
        invocation_kind: str,
        command_id: str,
        title: str,
        duration_ms: int | None,
        success: bool,
        message: str,
        action_json: str | None,
        context: ShellContext | None,
    ) -> None:
        """
        Пишет запись о запуске в SQLite.
        """
        self._state_store.add_run_log(
            invocation_kind=invocation_kind,
            command_id=command_id,
            title=title,
            duration_ms=duration_ms,
            success=success,
            message=message,
            action_json=action_json,
            context_json=context.model_dump_json() if context is not None else None,
        )

    def _invoke_oneshot(
        self,
        manifest: OneshotScriptManifest,
        context: InvocationContext | None,
    ) -> MenuInvocationResult:
        """
        Реально выполняет oneshot-скрипт в отдельном процессе.
        """
        shell_context = self._to_shell_context(context)
        parameter_values = self._state_store.get_parameter_values(manifest.id)

        request = OneshotExecutionRequest(
            scripts_root=str(self._scripts_root),
            source_file=manifest.source_file,
            qualname=manifest.qualname,
            context=shell_context,
            parameter_values=parameter_values,
        )

        response = execute_oneshot_in_subprocess(request)

        if isinstance(response, ExecutionErrorResponse):
            message = (
                f"Скрипт '{manifest.title}' завершился ошибкой: "
                f"{response.error_type}: {response.message}"
            )
            self._add_run_log(
                invocation_kind="oneshot_script",
                command_id=manifest.id,
                title=manifest.title,
                duration_ms=None,
                success=False,
                message=message,
                action_json=None,
                context=shell_context,
            )
            return MenuInvocationResult(
                accepted=False,
                message=message,
            )

        action_json = response.action.model_dump_json()
        action_description = describe_serialized_action(response.action)

        try:
            action_message = execute_serialized_action(response.action)
            final_message = (
                f"Скрипт '{manifest.title}' успешно выполнен за {response.duration_ms} мс. "
                f"{action_description} {action_message}"
            )
            accepted = True
        except Exception as error:  # noqa: BLE001
            final_message = (
                f"Скрипт '{manifest.title}' успешно выполнился за "
                f"{response.duration_ms} мс, но действие не удалось исполнить: {error}"
            )
            accepted = False

        self._add_run_log(
            invocation_kind="oneshot_script",
            command_id=manifest.id,
            title=manifest.title,
            duration_ms=response.duration_ms,
            success=True,
            message=final_message,
            action_json=action_json,
            context=shell_context,
        )

        return MenuInvocationResult(
            accepted=accepted,
            message=final_message,
        )

    def _invoke_service_script(
        self,
        service_id: str,
        script_manifest: ServiceScriptManifest,
        context: InvocationContext | None,
    ) -> MenuInvocationResult:
        """
        Реально вызывает метод уже запущенного сервиса.
        """
        shell_context = self._to_shell_context(context)

        response = self._service_manager.invoke_service_method(
            service_id,
            script_manifest,
            shell_context,
        )

        if isinstance(response, ServiceInvocationFailure):
            message = (
                f"Метод сервиса '{script_manifest.title}' завершился ошибкой: "
                f"{response.error_type}: {response.message}"
            )
            self._add_run_log(
                invocation_kind="service_script",
                command_id=script_manifest.id,
                title=script_manifest.title,
                duration_ms=None,
                success=False,
                message=message,
                action_json=None,
                context=shell_context,
            )
            return MenuInvocationResult(
                accepted=False,
                message=message,
            )

        action_json = response.action.model_dump_json()
        action_description = describe_serialized_action(response.action)

        try:
            action_message = execute_serialized_action(response.action)
            final_message = (
                f"Метод сервиса '{script_manifest.title}' успешно выполнен за "
                f"{response.duration_ms} мс. {action_description} {action_message}"
            )
            accepted = True
        except Exception as error:  # noqa: BLE001
            final_message = (
                f"Метод сервиса '{script_manifest.title}' успешно выполнился за "
                f"{response.duration_ms} мс, но действие не удалось исполнить: {error}"
            )
            accepted = False

        self._add_run_log(
            invocation_kind="service_script",
            command_id=script_manifest.id,
            title=script_manifest.title,
            duration_ms=response.duration_ms,
            success=True,
            message=final_message,
            action_json=action_json,
            context=shell_context,
        )

        return MenuInvocationResult(
            accepted=accepted,
            message=final_message,
        )

    def invoke(
        self, menu_item_id: str, context: InvocationContext
    ) -> MenuInvocationResult:
        """
        Валидирует выбранный пункт меню и запускает его.
        """
        with self._lock:
            command = next(
                (
                    item
                    for item in self._catalog.context_commands
                    if item.id == menu_item_id
                ),
                None,
            )

        oneshot_manifest = self._find_oneshot_script(menu_item_id)
        service_script_info = self._find_service_script(menu_item_id)

        if command is None:
            return MenuInvocationResult(
                accepted=False,
                message=f"Пункт меню '{menu_item_id}' не найден в текущем каталоге.",
            )

        if command.service_id is not None and not self._service_manager.is_running(
            command.service_id
        ):
            return MenuInvocationResult(
                accepted=False,
                message=(
                    f"Сервис '{command.service_id}' сейчас остановлен, "
                    "поэтому этот пункт меню недоступен."
                ),
            )

        if not matches_manifest_input_rules(command.input_rules, context):
            return MenuInvocationResult(
                accepted=False,
                message="Текущий shell-контекст не подходит для этого пункта меню.",
            )

        if oneshot_manifest is not None:
            return self._invoke_oneshot(oneshot_manifest, context)

        if service_script_info is not None:
            service_id, script_manifest = service_script_info
            return self._invoke_service_script(service_id, script_manifest, context)

        return MenuInvocationResult(
            accepted=False,
            message="Команда найдена в shell-каталоге, но не удалось определить её тип.",
        )

    def invoke_direct(self, owner_id: str) -> MenuInvocationResult:
        """
        Запускает скрипт или service.script без shell-контекста.

        Этот метод нужен для GUI-кнопки "Запустить" у сценариев,
        которые не требуют входных файлов.
        """
        oneshot_manifest = self._find_oneshot_script(owner_id)
        if oneshot_manifest is not None:
            if not oneshot_manifest.supports_direct_run:
                return MenuInvocationResult(
                    accepted=False,
                    message=(
                        f"Скрипт '{oneshot_manifest.title}' требует входной контекст "
                        "и не может быть запущен напрямую."
                    ),
                )
            return self._invoke_oneshot(oneshot_manifest, None)

        service_script_info = self._find_service_script(owner_id)
        if service_script_info is not None:
            service_id, script_manifest = service_script_info

            if not script_manifest.supports_direct_run:
                return MenuInvocationResult(
                    accepted=False,
                    message=(
                        f"Метод сервиса '{script_manifest.title}' требует входной контекст "
                        "и не может быть запущен напрямую."
                    ),
                )

            if not self._service_manager.is_running(service_id):
                return MenuInvocationResult(
                    accepted=False,
                    message=(
                        f"Сервис '{service_id}' сейчас остановлен. "
                        "Сначала запусти его на вкладке сервисов."
                    ),
                )

            return self._invoke_service_script(service_id, script_manifest, None)

        return MenuInvocationResult(
            accepted=False,
            message=f"Сущность '{owner_id}' не найдена.",
        )
