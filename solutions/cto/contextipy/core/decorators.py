from __future__ import annotations

"""Core decorators for registering Contextipy services and scripts."""

import inspect
from dataclasses import replace
from typing import Any, Callable, Iterable, Sequence, TypeVar, overload

from .metadata import (
    OneshotScriptMetadata,
    ParameterMetadata,
    ServiceMetadata,
    ServiceScriptMetadata,
)
from .params import NO_DEFAULT, Param
from .types import InputMarker

F = TypeVar("F", bound=Callable[..., Any])

_METADATA_ATTR = "__contextipy_metadata__"
_ID_REGISTRY: dict[str, str] = {}
_SERVICE_TARGETS: dict[str, Callable[..., Any] | type[Any]] = {}
_SERVICE_METADATA: dict[str, ServiceMetadata] = {}


class RegistrationError(ValueError):
    """Raised when decorator validation fails."""


def _require_text(
    value: str | None,
    *,
    decorator: str,
    field: str,
) -> str:
    if value is None or not value.strip():
        msg = f"{decorator}: {field} must be provided"
        raise RegistrationError(msg)
    return value.strip()


def _ensure_unique_id(identifier: str, *, decorator: str) -> None:
    existing = _ID_REGISTRY.get(identifier)
    if existing is not None:
        msg = (
            f"{decorator}: ID '{identifier}' is already registered by "
            f"{existing}"
        )
        raise RegistrationError(msg)
    _ID_REGISTRY[identifier] = decorator


def _normalize_inputs(
    inputs: Iterable[InputMarker[Any]],
    *,
    decorator: str,
) -> tuple[InputMarker[Any], ...]:
    markers: list[InputMarker[Any]] = []
    for marker in inputs:
        if not isinstance(marker, InputMarker):
            msg = f"{decorator}: accepted input {marker!r} is not an InputMarker"
            raise RegistrationError(msg)
        markers.append(marker)
    return tuple(markers)


def _prepare_signature(
    target: Callable[..., Any] | type[Any],
    *,
    decorator: str,
    require_return_annotation: bool = True,
) -> tuple[tuple[inspect.Parameter, ...], str]:
    if inspect.isclass(target):
        sig = inspect.signature(target.__init__)
        parameters = tuple(list(sig.parameters.values())[1:])  # drop self
        target_name = target.__name__
        require_return_annotation = False
    else:
        sig = inspect.signature(target)
        parameters = tuple(sig.parameters.values())
        target_name = getattr(target, "__name__", repr(target))

    for parameter in parameters:
        if parameter.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            # *args/**kwargs cannot be described via Param but are allowed without specs.
            continue
        if parameter.annotation is inspect.Parameter.empty:
            msg = (
                f"{decorator}: Parameter '{parameter.name}' in "
                f"'{target_name}' must have a type annotation"
            )
            raise RegistrationError(msg)

    if require_return_annotation and sig.return_annotation is inspect.Signature.empty:
        msg = f"{decorator}: '{target_name}' must declare a return type annotation"
        raise RegistrationError(msg)

    return parameters, target_name


def _resolve_parameter_metadata(
    parameters: Sequence[inspect.Parameter],
    param_specs: Sequence[Param],
    *,
    decorator: str,
    target_name: str,
) -> tuple[ParameterMetadata, ...]:
    spec_map: dict[str, Param] = {}
    for spec in param_specs:
        if spec.name in spec_map:
            msg = f"{decorator}: Duplicate Param definition for '{spec.name}'"
            raise RegistrationError(msg)
        spec_map[spec.name] = spec

    resolved: list[ParameterMetadata] = []
    for parameter in parameters:
        if parameter.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue

        spec = spec_map.pop(parameter.name, None)
        if spec is None:
            continue

        annotation = parameter.annotation
        if annotation is inspect.Parameter.empty:
            if spec.annotation is None:
                msg = (
                    f"{decorator}: Parameter '{parameter.name}' in "
                    f"'{target_name}' must declare a type annotation either in the "
                    "function signature or the Param specification"
                )
                raise RegistrationError(msg)
            annotation = spec.annotation
        elif spec.annotation is not None and annotation != spec.annotation:
            msg = (
                f"{decorator}: Parameter '{parameter.name}' in '{target_name}' has "
                f"annotation {annotation!r} which differs from Param annotation "
                f"{spec.annotation!r}"
            )
            raise RegistrationError(msg)

        default = (
            parameter.default
            if parameter.default is not inspect.Parameter.empty
            else NO_DEFAULT
        )
        if spec.default is not NO_DEFAULT:
            if default is NO_DEFAULT:
                msg = (
                    f"{decorator}: Param for '{parameter.name}' specifies a default "
                    "but the function parameter does not"
                )
                raise RegistrationError(msg)
            if default != spec.default:
                msg = (
                    f"{decorator}: Default mismatch for '{parameter.name}' in "
                    f"'{target_name}': function={default!r}, Param={spec.default!r}"
                )
                raise RegistrationError(msg)
            default = spec.default

        required = spec.required if spec.required is not None else default is NO_DEFAULT

        resolved.append(
            ParameterMetadata(
                name=parameter.name,
                title=spec.title,
                description=spec.description,
                annotation=annotation,
                required=required,
                default=default,
            )
        )

    if spec_map:
        missing = ", ".join(sorted(spec_map))
        msg = (
            f"{decorator}: Param definitions provided for unknown parameters: {missing}"
        )
        raise RegistrationError(msg)

    return tuple(resolved)


def _register_service_metadata(
    metadata: ServiceMetadata,
) -> None:
    _SERVICE_TARGETS[metadata.id] = metadata.target
    _SERVICE_METADATA[metadata.id] = metadata


def _lookup_service_metadata(
    service_id: str,
    *,
    decorator: str,
) -> ServiceMetadata:
    try:
        return _SERVICE_METADATA[service_id]
    except KeyError as exc:
        msg = f"{decorator}: Service '{service_id}' has not been registered"
        raise RegistrationError(msg) from exc


def oneshot_script(
    *,
    script_id: str,
    title: str,
    description: str,
    timeout: float | None = None,
    accepts: Iterable[InputMarker[Any]] = (),
    params: Sequence[Param] = (),
) -> Callable[[F], F]:
    """Decorator that registers a oneshot script function."""

    script_id = _require_text(script_id, decorator="@oneshot_script", field="script_id")
    title = _require_text(title, decorator="@oneshot_script", field="title")
    description = _require_text(
        description,
        decorator="@oneshot_script",
        field="description",
    )

    def decorator(func: F) -> F:
        if inspect.isclass(func):
            msg = "@oneshot_script can only decorate functions"
            raise RegistrationError(msg)

        parameters, target_name = _prepare_signature(
            func,
            decorator="@oneshot_script",
            require_return_annotation=True,
        )
        _ensure_unique_id(script_id, decorator="@oneshot_script")

        metadata = OneshotScriptMetadata(
            id=script_id,
            title=title,
            description=description,
            timeout=timeout,
            accepts=_normalize_inputs(accepts, decorator="@oneshot_script"),
            parameters=_resolve_parameter_metadata(
                parameters,
                params,
                decorator="@oneshot_script",
                target_name=target_name,
            ),
            target=func,
        )

        setattr(func, _METADATA_ATTR, metadata)
        return func

    return decorator


def service(
    *,
    service_id: str,
    title: str,
    description: str,
    timeout: float | None = None,
    accepts: Iterable[InputMarker[Any]] = (),
    params: Sequence[Param] = (),
) -> Callable[[F], F]:
    """Decorator that registers a long-running service."""

    service_id = _require_text(service_id, decorator="@service", field="service_id")
    title = _require_text(title, decorator="@service", field="title")
    description = _require_text(description, decorator="@service", field="description")

    def decorator(func: F) -> F:
        parameters, target_name = _prepare_signature(
            func,
            decorator="@service",
            require_return_annotation=True,
        )
        _ensure_unique_id(service_id, decorator="@service")

        metadata = ServiceMetadata(
            id=service_id,
            title=title,
            description=description,
            timeout=timeout,
            accepts=_normalize_inputs(accepts, decorator="@service"),
            parameters=_resolve_parameter_metadata(
                parameters,
                params,
                decorator="@service",
                target_name=target_name,
            ),
            target=func,
            service_scripts=(),
        )

        setattr(func, _METADATA_ATTR, metadata)
        _register_service_metadata(metadata)
        return func

    return decorator


def service_script(
    *,
    script_id: str,
    service_id: str,
    title: str,
    description: str,
    timeout: float | None = None,
    accepts: Iterable[InputMarker[Any]] = (),
    params: Sequence[Param] = (),
) -> Callable[[F], F]:
    """Decorator that registers a script operating on a service."""

    script_id = _require_text(script_id, decorator="@service_script", field="script_id")
    service_id = _require_text(
        service_id,
        decorator="@service_script",
        field="service_id",
    )
    title = _require_text(title, decorator="@service_script", field="title")
    description = _require_text(
        description,
        decorator="@service_script",
        field="description",
    )

    def decorator(func: F) -> F:
        if inspect.isclass(func):
            msg = "@service_script can only decorate functions"
            raise RegistrationError(msg)

        parameters, target_name = _prepare_signature(
            func,
            decorator="@service_script",
            require_return_annotation=True,
        )

        service_metadata = _lookup_service_metadata(
            service_id,
            decorator="@service_script",
        )
        _ensure_unique_id(script_id, decorator="@service_script")

        metadata = ServiceScriptMetadata(
            id=script_id,
            title=title,
            description=description,
            timeout=timeout,
            accepts=_normalize_inputs(accepts, decorator="@service_script"),
            parameters=_resolve_parameter_metadata(
                parameters,
                params,
                decorator="@service_script",
                target_name=target_name,
            ),
            service_id=service_metadata.id,
            target=func,
        )

        setattr(func, _METADATA_ATTR, metadata)

        updated_service_metadata = replace(
            service_metadata,
            service_scripts=service_metadata.service_scripts + (metadata,),
        )
        _SERVICE_METADATA[service_id] = updated_service_metadata
        service_target = _SERVICE_TARGETS[service_id]
        setattr(service_target, _METADATA_ATTR, updated_service_metadata)

        return func

    return decorator


def get_metadata(
    target: Callable[..., Any] | type[Any],
) -> OneshotScriptMetadata | ServiceMetadata | ServiceScriptMetadata | None:
    """Return metadata attached to a target, if any."""

    return getattr(target, _METADATA_ATTR, None)


__all__ = [
    "oneshot_script",
    "service",
    "service_script",
    "get_metadata",
    "RegistrationError",
]
