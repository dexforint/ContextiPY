from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


DefinitionKind = Literal["oneshot_script", "service", "service_script"]

# Эти имена атрибутов мы вешаем на функции и классы.
# Позже регистратор будет искать их при анализе пользовательских модулей.
P_CONTEXT_DEFINITION_ATTR = "__pcontext_definition__"
P_CONTEXT_SERVICE_BINDER_ATTR = "__pcontext_service_binder__"


@dataclass(frozen=True, slots=True)
class CommonDefinitionOptions:
    """
    Общие поля для любого элемента PContext.

    Эти данные попадают в индекс зарегистрированных скриптов и сервисов,
    а затем используются в UI и в контекстном меню.
    """

    id: str | None
    title: str
    description: str | None = None
    icon: str | None = None


@dataclass(frozen=True, slots=True)
class OneshotScriptOptions(CommonDefinitionOptions):
    """
    Настройки одноразового скрипта.
    """

    timeout: int | None = None


@dataclass(frozen=True, slots=True)
class ServiceOptions(CommonDefinitionOptions):
    """
    Настройки сервиса.
    """

    timeout: int | None = None
    max_downtime: int | None = None
    on_startup: bool = False


@dataclass(frozen=True, slots=True)
class ServiceScriptOptions(CommonDefinitionOptions):
    """
    Настройки метода сервиса, который вызывается как отдельный пункт меню.
    """

    timeout: int | None = None


DefinitionOptions = OneshotScriptOptions | ServiceOptions | ServiceScriptOptions


@dataclass(frozen=True, slots=True)
class DefinitionEnvelope:
    """
    Обёртка над декларацией.

    Мы явно храним тип сущности, чтобы регистратор мог одинаково читать
    метаданные и у функций, и у классов.
    """

    kind: DefinitionKind
    options: DefinitionOptions