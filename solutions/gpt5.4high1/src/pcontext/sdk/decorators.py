from __future__ import annotations

from typing import Any, Callable, TypeVar
from uuid import uuid4

from pcontext.metadata import (
    DefinitionEnvelope,
    OneshotScriptOptions,
    P_CONTEXT_DEFINITION_ATTR,
    P_CONTEXT_SERVICE_BINDER_ATTR,
    ServiceOptions,
    ServiceScriptOptions,
)


_TCallable = TypeVar("_TCallable", bound=Callable[..., Any])
_TServiceInstance = TypeVar("_TServiceInstance", bound=object)


def _validate_title(title: str) -> None:
    """
    Проверяет, что человекочитаемое имя действительно задано.
    """
    if not title.strip():
        raise ValueError("Поле title не может быть пустым.")


def _validate_timeout(name: str, value: int | None) -> None:
    """
    Проверяет ограничение на время в секундах.
    """
    if value is not None and value <= 0:
        raise ValueError(f"Поле {name} должно быть положительным числом.")


def _validate_icon(icon: str | None) -> None:
    """
    Проверяет ссылку на иконку.

    Пока здесь только базовая проверка. Позже регистратор будет отдельно
    подтверждать существование файла и корректность формата.
    """
    if icon is not None and not icon.strip():
        raise ValueError("Поле icon не может быть пустой строкой.")


def oneshot_script(
    *,
    title: str,
    description: str | None = None,
    timeout: int | None = None,
    icon: str | None = None,
    id: str | None = None,
) -> Callable[[_TCallable], _TCallable]:
    """
    Декоратор для обычного скрипта, который запускается на каждый вызов отдельно.
    """
    _validate_title(title)
    _validate_timeout("timeout", timeout)
    _validate_icon(icon)

    options = OneshotScriptOptions(
        id=id,
        title=title,
        description=description,
        timeout=timeout,
        icon=icon,
    )

    def decorator(function: _TCallable) -> _TCallable:
        envelope = DefinitionEnvelope(kind="oneshot_script", options=options)
        setattr(function, P_CONTEXT_DEFINITION_ATTR, envelope)
        return function

    return decorator


class Service:
    """
    Фабрика декораторов для описания сервиса и его методов.

    Пример:
        service = Service()

        @service(title="Мой сервис")
        class MyService:
            ...

            @service.script(title="Сделать действие")
            def run(self) -> None:
                ...
    """

    def __init__(self) -> None:
        # Токен нужен, чтобы регистратор мог понять, какие методы
        # принадлежат какому именно сервису.
        self._binder_token = uuid4().hex

    def __call__(
        self,
        *,
        title: str,
        description: str | None = None,
        timeout: int | None = None,
        max_downtime: int | None = None,
        on_startup: bool = False,
        icon: str | None = None,
        id: str | None = None,
    ) -> Callable[[type[_TServiceInstance]], type[_TServiceInstance]]:
        """
        Декоратор класса сервиса.
        """
        _validate_title(title)
        _validate_timeout("timeout", timeout)
        _validate_timeout("max_downtime", max_downtime)
        _validate_icon(icon)

        options = ServiceOptions(
            id=id,
            title=title,
            description=description,
            timeout=timeout,
            max_downtime=max_downtime,
            on_startup=on_startup,
            icon=icon,
        )

        def decorator(service_class: type[_TServiceInstance]) -> type[_TServiceInstance]:
            envelope = DefinitionEnvelope(kind="service", options=options)
            setattr(service_class, P_CONTEXT_DEFINITION_ATTR, envelope)
            setattr(service_class, P_CONTEXT_SERVICE_BINDER_ATTR, self._binder_token)
            return service_class

        return decorator

    def script(
        self,
        *,
        title: str,
        description: str | None = None,
        timeout: int | None = None,
        icon: str | None = None,
        id: str | None = None,
    ) -> Callable[[_TCallable], _TCallable]:
        """
        Декоратор метода сервиса, который должен стать пунктом контекстного меню.
        """
        _validate_title(title)
        _validate_timeout("timeout", timeout)
        _validate_icon(icon)

        options = ServiceScriptOptions(
            id=id,
            title=title,
            description=description,
            timeout=timeout,
            icon=icon,
        )

        def decorator(function: _TCallable) -> _TCallable:
            envelope = DefinitionEnvelope(kind="service_script", options=options)
            setattr(function, P_CONTEXT_DEFINITION_ATTR, envelope)
            setattr(function, P_CONTEXT_SERVICE_BINDER_ATTR, self._binder_token)
            return function

        return decorator


def get_definition(obj: object) -> DefinitionEnvelope | None:
    """
    Возвращает декларацию PContext, если она есть на объекте.
    """
    value = getattr(obj, P_CONTEXT_DEFINITION_ATTR, None)
    if isinstance(value, DefinitionEnvelope):
        return value
    return None


def get_service_binder_token(obj: object) -> str | None:
    """
    Возвращает внутренний токен сервиса.

    Он нужен регистратору для связывания класса сервиса и его методов.
    """
    value = getattr(obj, P_CONTEXT_SERVICE_BINDER_ATTR, None)
    if isinstance(value, str):
        return value
    return None