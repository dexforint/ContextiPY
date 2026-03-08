from __future__ import annotations

from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from pcontext.runtime.question_models import AskUserRequest, AskUserResponse


PROTOCOL_VERSION = 1


class StrictModel(BaseModel):
    """
    Базовая модель протокола.
    """

    model_config = ConfigDict(extra="forbid")


class ShellEntry(StrictModel):
    """
    Один объект, выбранный в файловом менеджере.
    """

    path: str
    entry_type: Literal["file", "folder"]


class ShellContext(StrictModel):
    """
    Контекст вызова контекстного меню.
    """

    source: Literal["selection", "background"]
    current_folder: str | None = None
    entries: list[ShellEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_invariants(self) -> "ShellContext":
        """
        Проверяет, что контекст собран логически корректно.
        """
        if self.source == "background":
            if self.entries:
                raise ValueError(
                    "Для background-контекста список entries должен быть пустым."
                )
            if not self.current_folder:
                raise ValueError("Для background-контекста нужен current_folder.")

        if self.source == "selection" and not self.entries:
            raise ValueError(
                "Для selection-контекста нужен хотя бы один выбранный объект."
            )

        return self


class MenuItemDescriptor(StrictModel):
    """
    Один пункт меню, который агент просит показать в подменю PContext.
    """

    id: str
    title: str
    icon: str | None = None
    enabled: bool = True


class ServiceDescriptor(StrictModel):
    """
    Сводка по сервису для окна управления и CLI.
    """

    service_id: str
    title: str
    running: bool
    on_startup: bool
    script_count: int


class AgentEndpoint(StrictModel):
    """
    Данные для подключения к запущенному агенту.
    """

    protocol_version: Literal[1] = PROTOCOL_VERSION
    host: str
    port: int
    token: str
    pid: int


class PingRequest(StrictModel):
    kind: Literal["ping"] = "ping"
    protocol_version: Literal[1] = PROTOCOL_VERSION
    token: str


class QueryMenuRequest(StrictModel):
    kind: Literal["query_menu"] = "query_menu"
    protocol_version: Literal[1] = PROTOCOL_VERSION
    token: str
    context: ShellContext


class InvokeMenuItemRequest(StrictModel):
    kind: Literal["invoke_menu_item"] = "invoke_menu_item"
    protocol_version: Literal[1] = PROTOCOL_VERSION
    token: str
    menu_item_id: str
    context: ShellContext


class ReloadRegistryRequest(StrictModel):
    kind: Literal["reload_registry"] = "reload_registry"
    protocol_version: Literal[1] = PROTOCOL_VERSION
    token: str


class ListServicesRequest(StrictModel):
    kind: Literal["list_services"] = "list_services"
    protocol_version: Literal[1] = PROTOCOL_VERSION
    token: str


class StartServiceRequest(StrictModel):
    kind: Literal["start_service"] = "start_service"
    protocol_version: Literal[1] = PROTOCOL_VERSION
    token: str
    service_id: str


class StopServiceRequest(StrictModel):
    kind: Literal["stop_service"] = "stop_service"
    protocol_version: Literal[1] = PROTOCOL_VERSION
    token: str
    service_id: str


class OpenMenuChooserRequest(StrictModel):
    """
    Просит агент открыть GUI-chooser и затем выполнить выбранную команду.
    """

    kind: Literal["open_menu_chooser"] = "open_menu_chooser"
    protocol_version: Literal[1] = PROTOCOL_VERSION
    token: str
    context: ShellContext


class RecordLauncherEventRequest(StrictModel):
    """
    Просит агент записать launcher-вызов в общие логи PContext.
    """

    kind: Literal["record_launcher_event"] = "record_launcher_event"
    protocol_version: Literal[1] = PROTOCOL_VERSION
    token: str
    event_id: str
    title: str
    message: str
    success: bool
    context: ShellContext | None = None


RequestMessage: TypeAlias = Annotated[
    PingRequest
    | QueryMenuRequest
    | InvokeMenuItemRequest
    | ReloadRegistryRequest
    | ListServicesRequest
    | StartServiceRequest
    | StopServiceRequest
    | AskUserRequest
    | OpenMenuChooserRequest
    | RecordLauncherEventRequest,
    Field(discriminator="kind"),
]

REQUEST_ADAPTER = TypeAdapter(RequestMessage)


class ErrorResponse(StrictModel):
    kind: Literal["error"] = "error"
    ok: Literal[False] = False
    protocol_version: Literal[1] = PROTOCOL_VERSION
    error_code: str
    message: str


class PingResponse(StrictModel):
    kind: Literal["ping_result"] = "ping_result"
    ok: Literal[True] = True
    protocol_version: Literal[1] = PROTOCOL_VERSION
    pid: int


class QueryMenuResponse(StrictModel):
    kind: Literal["query_menu_result"] = "query_menu_result"
    ok: Literal[True] = True
    protocol_version: Literal[1] = PROTOCOL_VERSION
    items: list[MenuItemDescriptor]


class InvokeMenuItemResponse(StrictModel):
    kind: Literal["invoke_menu_item_result"] = "invoke_menu_item_result"
    ok: Literal[True] = True
    protocol_version: Literal[1] = PROTOCOL_VERSION
    accepted: bool
    message: str


class ReloadRegistryResponse(StrictModel):
    kind: Literal["reload_registry_result"] = "reload_registry_result"
    ok: Literal[True] = True
    protocol_version: Literal[1] = PROTOCOL_VERSION
    command_count: int
    service_count: int
    failure_count: int


class ListServicesResponse(StrictModel):
    kind: Literal["list_services_result"] = "list_services_result"
    ok: Literal[True] = True
    protocol_version: Literal[1] = PROTOCOL_VERSION
    services: list[ServiceDescriptor]


class StartServiceResponse(StrictModel):
    kind: Literal["start_service_result"] = "start_service_result"
    ok: Literal[True] = True
    protocol_version: Literal[1] = PROTOCOL_VERSION
    service_id: str
    accepted: bool
    running: bool
    message: str


class StopServiceResponse(StrictModel):
    kind: Literal["stop_service_result"] = "stop_service_result"
    ok: Literal[True] = True
    protocol_version: Literal[1] = PROTOCOL_VERSION
    service_id: str
    accepted: bool
    running: bool
    message: str


class OpenMenuChooserResponse(StrictModel):
    """
    Результат GUI-chooser запроса.
    """

    kind: Literal["open_menu_chooser_result"] = "open_menu_chooser_result"
    ok: Literal[True] = True
    protocol_version: Literal[1] = PROTOCOL_VERSION
    cancelled: bool
    accepted: bool
    message: str


class RecordLauncherEventResponse(StrictModel):
    """
    Ответ после записи launcher-события в лог.
    """

    kind: Literal["record_launcher_event_result"] = "record_launcher_event_result"
    ok: Literal[True] = True
    protocol_version: Literal[1] = PROTOCOL_VERSION
    recorded: bool


ResponseMessage: TypeAlias = Annotated[
    ErrorResponse
    | PingResponse
    | QueryMenuResponse
    | InvokeMenuItemResponse
    | ReloadRegistryResponse
    | ListServicesResponse
    | StartServiceResponse
    | StopServiceResponse
    | AskUserResponse
    | OpenMenuChooserResponse
    | RecordLauncherEventResponse,
    Field(discriminator="kind"),
]

RESPONSE_ADAPTER = TypeAdapter(ResponseMessage)
