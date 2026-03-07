from __future__ import annotations

from typing import Annotated, Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from pcontext.runtime.action_codec import SerializedAction
from pcontext.runtime.ipc_models import ShellContext


class StrictModel(BaseModel):
    """
    Базовая строгая модель service-host протокола.
    """

    model_config = ConfigDict(extra="forbid")


class ServiceStartRequest(StrictModel):
    """
    Запрос на запуск сервиса.
    """

    kind: Literal["start"] = "start"
    scripts_root: str
    source_file: str
    service_qualname: str
    parameter_values: dict[str, Any] = Field(default_factory=dict)


class ServiceInvokeRequest(StrictModel):
    """
    Запрос на вызов метода уже запущенного сервиса.
    """

    kind: Literal["invoke"] = "invoke"
    method_name: str
    context: ShellContext | None = None
    parameter_values: dict[str, Any] = Field(default_factory=dict)


class ServiceShutdownRequest(StrictModel):
    """
    Запрос на корректную остановку сервиса.
    """

    kind: Literal["shutdown"] = "shutdown"


class ServicePingRequest(StrictModel):
    """
    Простейшая проверка, что service-host жив.
    """

    kind: Literal["ping"] = "ping"


ServiceRequest: TypeAlias = Annotated[
    ServiceStartRequest
    | ServiceInvokeRequest
    | ServiceShutdownRequest
    | ServicePingRequest,
    Field(discriminator="kind"),
]

SERVICE_REQUEST_ADAPTER = TypeAdapter(ServiceRequest)


class ServiceStartedResponse(StrictModel):
    """
    Успешный запуск сервиса.
    """

    kind: Literal["started"] = "started"
    ok: Literal[True] = True
    duration_ms: int


class ServiceInvokeSuccessResponse(StrictModel):
    """
    Успешный вызов метода сервиса.
    """

    kind: Literal["invoke_success"] = "invoke_success"
    ok: Literal[True] = True
    action: SerializedAction
    duration_ms: int


class ServiceShutdownResponse(StrictModel):
    """
    Успешная остановка сервиса.
    """

    kind: Literal["shutdown_result"] = "shutdown_result"
    ok: Literal[True] = True


class ServicePongResponse(StrictModel):
    """
    Ответ на ping.
    """

    kind: Literal["pong"] = "pong"
    ok: Literal[True] = True


class ServiceErrorResponse(StrictModel):
    """
    Структурированная ошибка service-host процесса.
    """

    kind: Literal["error"] = "error"
    ok: Literal[False] = False
    phase: Literal["protocol", "start", "invoke", "shutdown"]
    error_type: str
    message: str
    traceback: str


ServiceResponse: TypeAlias = Annotated[
    ServiceStartedResponse
    | ServiceInvokeSuccessResponse
    | ServiceShutdownResponse
    | ServicePongResponse
    | ServiceErrorResponse,
    Field(discriminator="kind"),
]

SERVICE_RESPONSE_ADAPTER = TypeAdapter(ServiceResponse)
