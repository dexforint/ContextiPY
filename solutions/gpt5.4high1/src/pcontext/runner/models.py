from __future__ import annotations

from typing import Annotated, Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from pcontext.runtime.action_codec import SerializedAction
from pcontext.runtime.ipc_models import ShellContext


class StrictModel(BaseModel):
    """
    Базовая строгая модель runner-протокола.
    """

    model_config = ConfigDict(extra="forbid")


class OneshotExecutionRequest(StrictModel):
    """
    Запрос на выполнение обычного oneshot-скрипта.
    """

    kind: Literal["oneshot"] = "oneshot"
    scripts_root: str
    source_file: str
    qualname: str
    context: ShellContext | None = None
    parameter_values: dict[str, Any] = Field(default_factory=dict)


class ExecutionSuccessResponse(StrictModel):
    """
    Успешный результат выполнения скрипта.
    """

    kind: Literal["success"] = "success"
    ok: Literal[True] = True
    action: SerializedAction
    duration_ms: int


class ExecutionErrorResponse(StrictModel):
    """
    Ошибка выполнения скрипта.
    """

    kind: Literal["error"] = "error"
    ok: Literal[False] = False
    error_type: str
    message: str
    traceback: str


ExecutionResponse: TypeAlias = Annotated[
    ExecutionSuccessResponse | ExecutionErrorResponse,
    Field(discriminator="kind"),
]

EXECUTION_REQUEST_ADAPTER = TypeAdapter(OneshotExecutionRequest)
EXECUTION_RESPONSE_ADAPTER = TypeAdapter(ExecutionResponse)
