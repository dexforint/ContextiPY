from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pcontext.agent.server import AgentApplication
from pcontext.agent.service_manager import ServiceControlResult, ServiceStatusView
from pcontext.registrar.models import ParamArgumentManifest
from pcontext.runtime.action_codec import SERIALIZED_ACTION_ADAPTER
from pcontext.runtime.action_executor import execute_serialized_action
from pcontext.storage.models import RunLogRecord


@dataclass(frozen=True, slots=True)
class ScriptListItem:
    """
    Одна строка вкладки со скриптами.
    """

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
    """
    Полная информация о владельце параметров.
    """

    owner_id: str
    owner_title: str
    owner_kind: Literal["oneshot_script", "service", "service_script"]
    parameters: tuple[ParamArgumentManifest, ...]
    current_values: dict[str, Any]


class GuiBackend:
    """
    Небольшой фасад над AgentApplication для GUI-слоя.
    """

    SETTINGS_AUTOSTART = "settings.launch_on_startup"
    SETTINGS_DISABLE_NOTIFICATIONS = "settings.disable_notifications"

    def __init__(self, application: AgentApplication) -> None:
        self._application = application

    @property
    def application(self) -> AgentApplication:
        """
        Возвращает низкоуровневое приложение-агент.
        """
        return self._application

    def reload_registry(self) -> tuple[int, int, int]:
        """
        Перезагружает каталог пользовательских скриптов.
        """
        result = self._application.registry.reload()
        return result.command_count, result.service_count, result.failure_count

    def list_services(self) -> list[ServiceStatusView]:
        """
        Возвращает текущее состояние сервисов.
        """
        return self._application.registry.list_services()

    def start_service(self, service_id: str) -> ServiceControlResult:
        """
        Запускает сервис.
        """
        return self._application.registry.start_service(service_id)

    def stop_service(self, service_id: str) -> ServiceControlResult:
        """
        Останавливает сервис.
        """
        return self._application.registry.stop_service(service_id)

    def list_script_items(self) -> list[ScriptListItem]:
        """
        Возвращает все скрипты и service.script-методы в удобном виде для таблицы GUI.
        """
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
        """
        Возвращает полную информацию о сущности, у которой можно редактировать параметры.
        """
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
        """
        Сохраняет параметры сущности.

        Мы сначала сбрасываем старые override-значения, а затем сохраняем
        только те поля, которые реально отличаются от default.
        """
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
        """
        Сбрасывает все сохранённые параметры сущности.
        """
        return self._application.state_store.reset_all_parameter_values(owner_id)

    def invoke_direct(self, owner_id: str) -> tuple[bool, str]:
        """
        Запускает сценарий без shell-контекста.
        """
        result = self._application.registry.invoke_direct(owner_id)
        return result.accepted, result.message

    def list_logs(self, limit: int = 50) -> list[RunLogRecord]:
        """
        Возвращает последние записи логов.
        """
        return self._application.state_store.list_run_logs(limit=limit)

    def replay_log_action(self, log_id: int) -> str:
        """
        Повторяет сохранённое действие из лога.
        """
        log_record = self._application.state_store.get_run_log(log_id)
        if log_record is None:
            raise RuntimeError(f"Запись лога с id={log_id} не найдена.")

        if log_record.action_json is None:
            raise RuntimeError("У этой записи нет сохранённого действия для повтора.")

        action = SERIALIZED_ACTION_ADAPTER.validate_json(log_record.action_json)
        return execute_serialized_action(action)

    def get_setting(self, key: str, default: Any) -> Any:
        """
        Читает настройку приложения.
        """
        return self._application.state_store.get_setting(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        """
        Сохраняет настройку приложения.
        """
        self._application.state_store.set_setting(key, value)
