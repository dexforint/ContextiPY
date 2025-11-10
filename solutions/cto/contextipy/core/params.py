from __future__ import annotations

"""Parameter specification utilities for scripts and services."""

from dataclasses import dataclass
from typing import Any


class _NoDefault:
    """Sentinel indicating that a parameter has no default value."""

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return "NO_DEFAULT"


NO_DEFAULT = _NoDefault()


@dataclass(frozen=True)
class Param:
    """Declarative parameter specification for Contextipy decorators.

    The metadata provided here is combined with the Python function signature to
    generate the runtime parameter metadata attached to services and scripts.
    """

    name: str
    title: str
    description: str
    annotation: type[Any] | None = None
    default: Any = NO_DEFAULT
    required: bool | None = None

    def __post_init__(self) -> None:
        if not self.name:
            msg = "Param must define a non-empty name"
            raise ValueError(msg)
        if not self.title:
            msg = "Param must define a non-empty title"
            raise ValueError(msg)
        if not self.description:
            msg = "Param must define a non-empty description"
            raise ValueError(msg)


__all__ = ["Param", "NO_DEFAULT"]
