from __future__ import annotations

"""Core type markers used by Contextipy service and script definitions."""

from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar


T_co = TypeVar("T_co", covariant=True)


@dataclass(frozen=True)
class InputMarker(Generic[T_co]):
    """Describes an accepted input type for a script or service.

    The marker captures a stable name as well as the Python type that values
    should conform to. These instances are intentionally lightweight and can
    be compared by their ``name`` attribute.
    """

    name: str
    python_type: type[T_co]
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.name:
            msg = "Input markers must define a non-empty name"
            raise ValueError(msg)

    def __repr__(self) -> str:  # pragma: no cover - convenience representation
        return f"InputMarker(name={self.name!r}, python_type={self.python_type!r})"


# Predefined markers commonly used by scripts and services.
File = InputMarker("file", Path)
Folder = InputMarker("folder", Path)
Image = InputMarker("image", Path)
Text = InputMarker("text", str)
Url = InputMarker("url", str)
Audio = InputMarker("audio", Path)
Video = InputMarker("video", Path)
Json = InputMarker("json", str)

__all__ = [
    "InputMarker",
    "File",
    "Folder",
    "Image",
    "Text",
    "Url",
    "Audio",
    "Video",
    "Json",
]
