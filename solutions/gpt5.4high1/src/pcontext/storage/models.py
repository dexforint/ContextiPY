from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


OwnerKind = Literal["oneshot_script", "service", "service_script"]


@dataclass(frozen=True, slots=True)
class ParameterValueView:
    """
    Текущее состояние одного настраиваемого параметра.
    """

    owner_kind: OwnerKind
    owner_id: str
    owner_title: str
    param_name: str
    default_value: Any
    current_value: Any
    has_override: bool


@dataclass(frozen=True, slots=True)
class RunLogRecord:
    """
    Запись лога одного запуска.
    """

    log_id: int
    created_at_utc: str
    invocation_kind: Literal["oneshot_script", "service_script", "launcher"]
    command_id: str
    title: str
    duration_ms: int | None
    success: bool
    message: str
    action_json: str | None
    context_json: str | None


@dataclass(frozen=True, slots=True)
class RegistrationModuleRecord:
    """
    Снимок регистрации одного Python-файла из папки scripts.
    """

    relative_path: str
    source_file: str
    file_hash_sha256: str
    dependencies: list[str]
    status: Literal["registered", "error"]
    error_message: str | None
    updated_at_utc: str


@dataclass(frozen=True, slots=True)
class CommandUsageStats:
    """
    Статистика использования конкретной команды.
    """

    command_id: str
    launch_count: int
    last_used_utc: str | None
