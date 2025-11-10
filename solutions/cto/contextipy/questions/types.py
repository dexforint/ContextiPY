from __future__ import annotations

"""Type definitions and metadata helpers for the questions engine."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Final, Generic, Sequence, TypeVar


T = TypeVar("T")


class _UnsetType:
    """Sentinel used to indicate that a value has not been provided."""

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return "UNSET"


UNSET: Final[_UnsetType] = _UnsetType()


@dataclass(frozen=True)
class Question(Generic[T]):
    """Base metadata for a question prompt."""

    title: str
    description: str | None = None
    default: Any = UNSET
    required: bool = True
    enum: Sequence[T] | None = None
    ge: float | None = None
    le: float | None = None
    kind: str = "text"
    serializer: Callable[[T], Any] | None = None
    deserializer: Callable[[Any], T] | None = None

    def __post_init__(self) -> None:
        if not self.title:
            msg = "Question must define a non-empty title"
            raise ValueError(msg)

        if self.enum is not None:
            if not self.enum:
                msg = "Question enum must contain at least one value"
                raise ValueError(msg)
            unique = set(self.enum)
            if len(unique) != len(tuple(self.enum)):
                msg = "Question enum values must be unique"
                raise ValueError(msg)
            object.__setattr__(self, "enum", tuple(self.enum))

        if self.ge is not None and self.le is not None and self.ge > self.le:
            msg = "Question ge constraint cannot be greater than le constraint"
            raise ValueError(msg)

    @property
    def has_default(self) -> bool:
        """Indicates whether a default value has been provided."""

        return self.default is not UNSET

    def serialize(self, value: T | None) -> Any:
        """Serialize a value for UI consumption."""

        if value is None:
            return None
        if self.serializer is not None:
            return self.serializer(value)
        return value

    def deserialize(self, value: Any) -> T | None:
        """Deserialize a value coming back from the UI."""

        if value is None:
            return None
        if self.deserializer is not None:
            return self.deserializer(value)
        return value  # type: ignore[return-value]


@dataclass(frozen=True, init=False)
class ImageQuery(Question[Path]):
    """Specialised question metadata requesting an image path."""

    formats: tuple[str, ...]

    def __init__(
        self,
        title: str,
        description: str | None = None,
        *,
        formats: Sequence[str] | None = None,
        required: bool = True,
        default: Path | str | None | _UnsetType = UNSET,
    ) -> None:
        available_formats = tuple(formats) if formats is not None else (
            "png",
            "jpg",
            "jpeg",
            "gif",
            "bmp",
            "webp",
        )

        def _serializer(value: Path) -> str:
            return str(value)

        def _deserializer(value: Any) -> Path:
            if isinstance(value, Path):
                return value
            if not isinstance(value, str):
                msg = "ImageQuery expects answers as path strings"
                raise TypeError(msg)
            return Path(value)

        normalized_default = default
        if isinstance(normalized_default, str):
            normalized_default = Path(normalized_default)

        super().__init__(
            title=title,
            description=description,
            default=normalized_default,
            required=required,
            enum=None,
            ge=None,
            le=None,
            kind="image",
            serializer=_serializer,  # type: ignore[arg-type]
            deserializer=_deserializer,
        )

        object.__setattr__(self, "formats", available_formats)

    def serialize(self, value: Path | None) -> Any:
        if value is None:
            return None
        return str(value)

    def deserialize(self, value: Any) -> Path | None:
        if value is None:
            return None
        if isinstance(value, Path):
            return value
        if not isinstance(value, str):
            msg = "ImageQuery expects answers as path strings"
            raise TypeError(msg)
        return Path(value)


__all__ = [
    "Question",
    "ImageQuery",
    "UNSET",
]
