from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pcontext.agent.server import AgentApplication
from pcontext.agent.service_manager import ServiceControlResult, ServiceStatusView
from pcontext.config import ensure_directories
from pcontext.gui.windows_shell_diagnostics import (
    WindowsShellDiagnostics,
    collect_windows_shell_diagnostics,
)
from pcontext.platform.windows.autostart import (
    WindowsAutostartInfo,
    get_windows_autostart_info,
    set_windows_autostart_enabled,
)
from pcontext.registrar.models import ParamArgumentManifest
from pcontext.registrar.registration import register_scripts
from pcontext.runtime.action_codec import (
    FolderActionModel,
    OpenAction,
    SERIALIZED_ACTION_ADAPTER,
)
from pcontext.runtime.action_executor import execute_serialized_action
from pcontext.runtime.python_env import (
    get_shared_venv_python,
    get_shared_venv_site_packages,
)
from pcontext.storage.models import RegistrationModuleRecord, RunLogRecord


@dataclass(frozen=True, slots=True)
class ScriptListItem:
    owner_id: str
    title: str
    description: str | None
    kind: Literal["oneshot_script", "service_script"]
    service_id: str | None
    service_title: str | None
    supports_direct_run: bool
    direct_run_enabled: bool
    parameter_count: int


@dataclass(frozen=True, slots=True)
class ParameterOwnerDetails:
    owner_id: str
    owner_title: str
    owner_kind: Literal["oneshot_script", "service", "service_script"]
    parameters: tuple[ParamArgumentManifest, ...]
    current_values: dict[str, Any]


@dataclass(frozen=True, slots=True)
class SharedVenvStatus:
    venv_dir: str
    python_executable: str
    site_packages_dir: str
    exists: bool


class GuiBackend:
    SETTINGS_AUTOSTART = "settings.launch_on_startup"
    SETTINGS_DISABLE_NOTIFICATIONS = "settings.disable_notifications"

    SETTINGS_CHOOSER_SORT = "chooser.sort_mode"
    SETTINGS_CHOOSER_GEOMETRY = "chooser.geometry"
    SETTINGS_CHOOSER_COLUMN_WIDTHS = "chooser.column_widths"

    def __init__(self, application: AgentApplication) -> None:
        self._application = application

    @property
    def application(self) -> AgentApplication:
        return self._application

    def get_windows_autostart_info(self) -> WindowsAutostartInfo:
        """
        Возвращает реальное состояние автозапуска Windows.
        """
        return get_windows_autostart_info()

    def set_windows_autostart(self, enabled: bool) -> None:
        """
        Применяет автозапуск Windows и сохраняет пользовательскую настройку.
        """
        set_windows_autostart_enabled(enabled)
        self._application.state_store.set_setting(self.SETTINGS_AUTOSTART, enabled)

    def register_and_reload(self) -> tuple[int, int, int, int, int, int, bool]:
        registration_result = register_scripts(
            self._application.paths,
            state_store=self._application.state_store,
        )
        self._application.registry.reload()

        return (
            registration_result.processed_files,
            registration_result.changed_files,
            registration_result.unchanged_files,
            registration_result.removed_files,
            registration_result.failed_files,
            registration_result.installed_dependency_groups,
            registration_result.venv_created,
        )

    def reload_registry(self) -> tuple[int, int, int]:
        result = self._application.registry.reload()
        return result.command_count, result.service_count, result.failure_count

    def open_scripts_folder(self) -> str:
        ensure_directories(self._application.paths)
        return execute_serialized_action(
            FolderActionModel(path=str(self._application.paths.scripts))
        )

    def open_runtime_folder(self) -> str:
        ensure_directories(self._application.paths)
        return execute_serialized_action(
            FolderActionModel(path=str(self._application.paths.runtime))
        )

    def open_launcher_log(self) -> str:
        ensure_directories(self._application.paths)
        log_path = self._application.paths.runtime / "windows-launcher.log"
        log_path.touch(exist_ok=True)
        return execute_serialized_action(OpenAction(path=str(log_path)))

    def open_registration_module_source(self, source_file: str) -> str:
        return execute_serialized_action(OpenAction(path=source_file))

    def get_windows_shell_diagnostics(self) -> WindowsShellDiagnostics:
        return collect_windows_shell_diagnostics(self._application.paths)

    def get_shared_venv_status(self) -> SharedVenvStatus:
        base_dir = self._application.paths.home
        python_path = get_shared_venv_python(base_dir)
        site_packages_path = get_shared_venv_site_packages(base_dir)

        return SharedVenvStatus(
            venv_dir=str(self._application.paths.venv),
            python_executable=str(python_path),
            site_packages_dir=str(site_packages_path),
            exists=python_path.is_file(),
        )

    def list_registration_modules(self) -> list[RegistrationModuleRecord]:
        return self._application.state_store.list_registration_modules()

    def list_failed_registration_modules(self) -> list[RegistrationModuleRecord]:
        return [
            item
            for item in self._application.state_store.list_registration_modules()
            if item.status == "error"
        ]

    def list_services(self) -> list[ServiceStatusView]:
        return self._application.registry.list_services()

    def start_service(self, service_id: str) -> ServiceControlResult:
        return self._application.registry.start_service(service_id)

    def stop_service(self, service_id: str) -> ServiceControlResult:
        return self._application.registry.stop_service(service_id)

    def list_script_items(self) -> list[ScriptListItem]:
        catalog = self._application.registry.catalog
        service_states = {
            item.service_id: item.running
            for item in self._application.registry.list_services()
        }

        items: list[ScriptListItem] = []

        for script in catalog.oneshot_scripts:
            items.append(
                ScriptListItem(
                    owner_id=script.id,
                    title=script.title,
                    description=script.description,
                    kind="oneshot_script",
                    service_id=None,
                    service_title=None,
                    supports_direct_run=script.supports_direct_run,
                    direct_run_enabled=script.supports_direct_run,
                    parameter_count=len(script.params),
                )
            )

        for service in catalog.services:
            service_running = service_states.get(service.id, False)

            for method in service.scripts:
                items.append(
                    ScriptListItem(
                        owner_id=method.id,
                        title=method.title,
                        description=method.description,
                        kind="service_script",
                        service_id=service.id,
                        service_title=service.title,
                        supports_direct_run=method.supports_direct_run,
                        direct_run_enabled=method.supports_direct_run
                        and service_running,
                        parameter_count=len(method.params),
                    )
                )

        return sorted(
            items,
            key=lambda item: (
                item.title.lower(),
                item.kind,
                item.owner_id,
            ),
        )

    def get_parameter_owner(self, owner_id: str) -> ParameterOwnerDetails | None:
        catalog = self._application.registry.catalog

        for script in catalog.oneshot_scripts:
            if script.id == owner_id:
                return ParameterOwnerDetails(
                    owner_id=script.id,
                    owner_title=script.title,
                    owner_kind="oneshot_script",
                    parameters=tuple(script.params),
                    current_values=self._application.state_store.get_parameter_values(
                        script.id
                    ),
                )

        for service in catalog.services:
            if service.id == owner_id:
                return ParameterOwnerDetails(
                    owner_id=service.id,
                    owner_title=service.title,
                    owner_kind="service",
                    parameters=tuple(service.init_params),
                    current_values=self._application.state_store.get_parameter_values(
                        service.id
                    ),
                )

            for method in service.scripts:
                if method.id == owner_id:
                    return ParameterOwnerDetails(
                        owner_id=method.id,
                        owner_title=method.title,
                        owner_kind="service_script",
                        parameters=tuple(method.params),
                        current_values=self._application.state_store.get_parameter_values(
                            method.id
                        ),
                    )

        return None

    def save_parameter_values(self, owner_id: str, values: dict[str, Any]) -> None:
        details = self.get_parameter_owner(owner_id)
        if details is None:
            raise RuntimeError(f"Владелец параметров '{owner_id}' не найден.")

        self._application.state_store.reset_all_parameter_values(owner_id)

        for parameter in details.parameters:
            current_value = values.get(parameter.name, parameter.default)
            if current_value != parameter.default:
                self._application.state_store.set_parameter_value(
                    owner_id,
                    parameter.name,
                    current_value,
                )

    def reset_parameter_values(self, owner_id: str) -> int:
        return self._application.state_store.reset_all_parameter_values(owner_id)

    def invoke_direct(self, owner_id: str) -> tuple[bool, str]:
        result = self._application.registry.invoke_direct(owner_id)
        return result.accepted, result.message

    def list_logs(self, limit: int = 50) -> list[RunLogRecord]:
        return self._application.state_store.list_run_logs(limit=limit)

    def replay_log_action(self, log_id: int) -> str:
        log_record = self._application.state_store.get_run_log(log_id)
        if log_record is None:
            raise RuntimeError(f"Запись лога с id={log_id} не найдена.")

        if log_record.action_json is None:
            raise RuntimeError("У этой записи нет сохранённого действия для повтора.")

        action = SERIALIZED_ACTION_ADAPTER.validate_json(log_record.action_json)
        return execute_serialized_action(action)

    def get_setting(self, key: str, default: Any) -> Any:
        return self._application.state_store.get_setting(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        self._application.state_store.set_setting(key, value)
