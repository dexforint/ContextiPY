from __future__ import annotations

"""Metadata classes describing registered services and scripts."""

from dataclasses import dataclass
from typing import Any, Callable, Tuple

from .types import InputMarker


@dataclass(frozen=True)
class ParameterMetadata:
    """Resolved metadata for a single function parameter."""

    name: str
    title: str
    description: str
    annotation: Any
    required: bool
    default: Any


@dataclass(frozen=True)
class BaseMetadata:
    """Common metadata fields shared by services and scripts."""

    id: str
    title: str
    description: str
    timeout: float | None
    accepts: Tuple[InputMarker[Any], ...]
    parameters: Tuple[ParameterMetadata, ...]

    @property
    def kind(self) -> str:  # pragma: no cover - implemented by subclasses
        raise NotImplementedError


@dataclass(frozen=True)
class OneshotScriptMetadata(BaseMetadata):
    """Metadata associated with a function decorated by @oneshot_script."""

    target: Callable[..., Any]

    @property
    def kind(self) -> str:
        return "oneshot"


@dataclass(frozen=True)
class ServiceScriptMetadata(BaseMetadata):
    """Metadata associated with a function decorated by @service_script."""

    service_id: str
    target: Callable[..., Any]

    @property
    def kind(self) -> str:
        return "service_script"


@dataclass(frozen=True)
class ServiceMetadata(BaseMetadata):
    """Metadata associated with a class or function decorated by @service."""

    target: Callable[..., Any] | type[Any]
    service_scripts: Tuple[ServiceScriptMetadata, ...]

    @property
    def kind(self) -> str:
        return "service"


__all__ = [
    "ParameterMetadata",
    "BaseMetadata",
    "OneshotScriptMetadata",
    "ServiceScriptMetadata",
    "ServiceMetadata",
]
