from __future__ import annotations

import inspect
from typing import Any, Annotated, get_args, get_origin, get_type_hints

from pydantic import TypeAdapter

from pcontext.runtime.ipc_models import ShellContext
from pcontext.runtime.matching import find_matching_input_spec
from pcontext.runtime.shell import normalize_shell_context
from pcontext.sdk.inputs import InputSpec, SelectionExpression
from pcontext.sdk.params import ParamSpec


def unwrap_annotated(annotation: Any) -> tuple[Any, list[Any]]:
    """
    Разворачивает `Annotated[T, ...]` в исходный тип и список метаданных.
    """
    if get_origin(annotation) is Annotated:
        parts = list(get_args(annotation))
        return parts[0], parts[1:]

    return annotation, []


def extract_bindings(
    annotation: Any,
) -> tuple[Any, SelectionExpression | None, ParamSpec | None]:
    """
    Извлекает из аннотации базовый тип и PContext-метаданные.
    """
    base_annotation, metadata_items = unwrap_annotated(annotation)

    input_binding: SelectionExpression | None = None
    param_binding: ParamSpec | None = None

    for metadata_item in metadata_items:
        if isinstance(metadata_item, SelectionExpression):
            if input_binding is not None:
                raise ValueError("Обнаружено больше одного input-описания у параметра.")
            input_binding = metadata_item
            continue

        if isinstance(metadata_item, ParamSpec):
            if param_binding is not None:
                raise ValueError("Обнаружено больше одного Param(...) у параметра.")
            param_binding = metadata_item

    if input_binding is not None and param_binding is not None:
        raise ValueError("Один параметр не может одновременно быть Input и Param.")

    return base_annotation, input_binding, param_binding


def resolve_object_by_qualname(module: object, qualname: str) -> Any:
    """
    Находит объект внутри модуля по полному `qualname`.
    """
    if "<locals>" in qualname:
        raise ValueError(
            "Локальные функции и классы не поддерживаются. "
            "Объявляй PContext-объекты только на уровне модуля."
        )

    current_object: Any = module

    for part in qualname.split("."):
        current_object = getattr(current_object, part)

    return current_object


def coerce_value(annotation: Any, raw_value: Any) -> Any:
    """
    Приводит сырое значение к типу, объявленному в аннотации.
    """
    adapter = TypeAdapter(annotation)
    return adapter.validate_python(raw_value)


def build_input_raw_value(binding: InputSpec, context: ShellContext) -> Any:
    """
    Преобразует shell-контекст в сырое значение аргумента функции.
    """
    normalized_context = normalize_shell_context(context)

    if binding.kind == "current_folder":
        if normalized_context.current_folder is None:
            raise ValueError("Для CurrentFolder() не удалось определить текущую папку.")
        return str(normalized_context.current_folder)

    if binding.multiple:
        return [str(entry.path) for entry in normalized_context.entries]

    if len(normalized_context.entries) != 1:
        raise ValueError("Ожидался ровно один выбранный объект.")

    return str(normalized_context.entries[0].path)


def build_callable_kwargs(
    callable_object: Any,
    *,
    context: ShellContext | None,
    parameter_values: dict[str, Any],
    skip_self: bool,
) -> dict[str, Any]:
    """
    Собирает именованные аргументы для вызова пользовательской функции или метода.
    """
    if inspect.iscoroutinefunction(callable_object):
        raise TypeError("Асинхронные обработчики пока не поддерживаются.")

    signature = inspect.signature(callable_object)
    type_hints = get_type_hints(callable_object, include_extras=True)
    kwargs: dict[str, Any] = {}

    for parameter_name, parameter in signature.parameters.items():
        if skip_self and parameter_name in {"self", "cls"}:
            continue

        if parameter.kind in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            raise TypeError(
                f"Параметр '{parameter_name}' использует *args/**kwargs, это не поддерживается."
            )

        annotation = type_hints.get(parameter_name, parameter.annotation)
        if annotation is inspect.Signature.empty:
            raise TypeError(
                f"У параметра '{parameter_name}' отсутствует аннотация типа."
            )

        base_annotation, input_binding, param_binding = extract_bindings(annotation)

        if input_binding is not None:
            if context is None:
                raise ValueError(
                    f"Для входного параметра '{parameter_name}' не передан shell-контекст."
                )

            matched_binding = find_matching_input_spec(
                input_binding,
                normalize_shell_context(context),
            )
            if matched_binding is None:
                raise ValueError(
                    f"Текущий shell-контекст не подходит для параметра '{parameter_name}'."
                )

            raw_value = build_input_raw_value(matched_binding, context)
            kwargs[parameter_name] = coerce_value(base_annotation, raw_value)
            continue

        if param_binding is not None:
            raw_value = parameter_values.get(parameter_name, param_binding.default)
            kwargs[parameter_name] = coerce_value(base_annotation, raw_value)
            continue

        raise TypeError(
            f"Параметр '{parameter_name}' не содержит ни Input-описания, ни Param(...)."
        )

    return kwargs
