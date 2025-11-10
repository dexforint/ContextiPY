from __future__ import annotations

import ast
import mimetypes
import re
import unicodedata
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from contextipy.core.types import Audio, File, Image, InputMarker, Json, Text, Video

__all__ = [
    "Extension",
    "detect_file_type",
    "get_mime_type",
    "is_valid_file_type",
    "sanitize_filename",
    "safe_join",
    "temp_directory",
    "validate_file_types",
]


_MARKER_BY_NAME: dict[str, InputMarker[Any]] = {
    "file": File,
    "image": Image,
    "video": Video,
    "audio": Audio,
    "text": Text,
    "json": Json,
}

_EXTENSION_TO_MARKER: dict[str, InputMarker[Any]] = {
    ".png": Image,
    ".jpg": Image,
    ".jpeg": Image,
    ".gif": Image,
    ".bmp": Image,
    ".webp": Image,
    ".svg": Image,
    ".tif": Image,
    ".tiff": Image,
    ".heif": Image,
    ".heic": Image,
    ".mp4": Video,
    ".mov": Video,
    ".m4v": Video,
    ".avi": Video,
    ".wmv": Video,
    ".flv": Video,
    ".mkv": Video,
    ".webm": Video,
    ".mp3": Audio,
    ".wav": Audio,
    ".flac": Audio,
    ".aac": Audio,
    ".ogg": Audio,
    ".oga": Audio,
    ".m4a": Audio,
    ".wma": Audio,
    ".txt": Text,
    ".md": Text,
    ".rtf": Text,
    ".json": Json,
}

_MIME_PREFIX_TO_MARKER: tuple[tuple[str, InputMarker[Any]], ...] = (
    ("image/", Image),
    ("video/", Video),
    ("audio/", Audio),
    ("text/", Text),
)

_MIME_EXACT_TO_MARKER: dict[str, InputMarker[Any]] = {
    "application/json": Json,
}

_INVALID_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def _literal_eval(text: str) -> Any:
    try:
        return ast.literal_eval(text)
    except (SyntaxError, ValueError) as exc:
        msg = "Extension specification must be valid Python literals"
        raise ValueError(msg) from exc


def _normalize_extension(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        msg = "Extension strings must not be empty"
        raise ValueError(msg)
    if not stripped.startswith("."):
        stripped = f".{stripped}"
    return stripped.lower()


def _extract_extension(path: Path) -> str | None:
    suffix = path.suffix
    if not suffix:
        return None
    return suffix.lower()


@dataclass(frozen=True)
class Extension:
    """Represents an allowed set of file extensions."""

    patterns: tuple[str, ...]

    def __init__(self, patterns: Sequence[str] | str) -> None:
        if isinstance(patterns, str):
            normalized = (_normalize_extension(patterns),)
        else:
            normalized = tuple(_normalize_extension(pattern) for pattern in patterns)
        if not normalized:
            msg = "Extension patterns must contain at least one value"
            raise ValueError(msg)
        object.__setattr__(self, "patterns", normalized)

    def matches(self, path: Path | str) -> bool:
        target = Path(path)
        extension = _extract_extension(target)
        if extension is None:
            return False
        return extension in self.patterns

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        options = ", ".join(self.patterns)
        return f"Extension([{options}])"


AllowedType = Extension | InputMarker[Any] | str
AllowedSpec = AllowedType | Sequence[AllowedType]


def get_mime_type(path: Path | str) -> str | None:
    """Return the MIME type for *path* using ``mimetypes`` detection."""

    mime, _ = mimetypes.guess_type(str(path))
    return mime


def detect_file_type(path: Path | str) -> InputMarker[Any]:
    """Attempt to detect the logical file type for *path*.

    The detection first checks known extension mappings before falling back to
    MIME type detection. If no specific match is found, ``File`` is returned as
    the most permissive type marker.
    """

    target = Path(path)
    extension = _extract_extension(target)
    if extension is not None and extension in _EXTENSION_TO_MARKER:
        return _EXTENSION_TO_MARKER[extension]

    mime = get_mime_type(target)
    if mime:
        if mime in _MIME_EXACT_TO_MARKER:
            return _MIME_EXACT_TO_MARKER[mime]
        for prefix, marker in _MIME_PREFIX_TO_MARKER:
            if mime.startswith(prefix):
                return marker

    return File


def _iter_spec(spec: AllowedSpec) -> Iterator[AllowedType]:
    if isinstance(spec, str) or not isinstance(spec, Iterable):
        yield spec  # type: ignore[misc]
        return
    if isinstance(spec, (bytes, bytearray)):
        msg = "Type specifications must be strings, InputMarkers, or Extension instances"
        raise TypeError(msg)
    for item in spec:
        yield item


def _parse_extension_spec(fragment: str) -> Extension:
    inside = fragment.strip()[len("extension(") : -1]
    inside = inside.strip()
    if not inside:
        msg = "Extension specifications must include at least one pattern"
        raise ValueError(msg)
    
    if inside.startswith("[") and inside.endswith("]"):
        list_content = inside[1:-1].strip()
        items = [item.strip() for item in list_content.split(",")]
        quoted_items = [f"'{item}'" if not (item.startswith(("'", '"')) and item.endswith(("'", '"'))) else item for item in items if item]
        text = f"[{', '.join(quoted_items)}]"
        value = _literal_eval(text)
    else:
        if "," in inside:
            items = [item.strip() for item in inside.split(",")]
            quoted_items = [f"'{item}'" if not (item.startswith(("'", '"')) and item.endswith(("'", '"'))) else item for item in items if item]
            text = f"[{', '.join(quoted_items)}]"
        else:
            if not (inside.startswith(("'", '"')) and inside.endswith(("'", '"'))):
                text = f"'{inside}'"
            else:
                text = inside
        value = _literal_eval(text)

    if isinstance(value, str):
        return Extension(value)
    if isinstance(value, Iterable):
        patterns = [str(item) for item in value]
        return Extension(patterns)
    msg = "Extension specification must evaluate to a string or iterable"
    raise ValueError(msg)


def _parse_string_spec(spec: str) -> list[Extension | InputMarker[Any]]:
    tokens = [token.strip() for token in spec.split("|") if token.strip()]
    if not tokens:
        msg = "Type specification string is empty"
        raise ValueError(msg)

    parsed: list[Extension | InputMarker[Any]] = []
    for token in tokens:
        lowered = token.lower()
        if lowered.startswith("extension(") and token.endswith(")"):
            parsed.append(_parse_extension_spec(token))
            continue
        marker = _MARKER_BY_NAME.get(lowered)
        if marker is None:
            msg = f"Unknown type specification: {token}"
            raise ValueError(msg)
        parsed.append(marker)
    return parsed


def _normalize_matchers(spec: AllowedSpec) -> tuple[Extension | InputMarker[Any], ...]:
    matchers: list[Extension | InputMarker[Any]] = []
    for item in _iter_spec(spec):
        if isinstance(item, Extension):
            matchers.append(item)
        elif isinstance(item, InputMarker):
            matchers.append(item)
        elif isinstance(item, str):
            matchers.extend(_parse_string_spec(item))
        else:  # pragma: no cover - defensive programming
            msg = (
                "Type specifications must be strings, InputMarker instances, "
                "or Extension definitions"
            )
            raise TypeError(msg)
    if not matchers:
        msg = "Type specifications must define at least one matcher"
        raise ValueError(msg)
    return tuple(matchers)


def _match_extension_or_marker(path: Path, matcher: Extension | InputMarker[Any]) -> bool:
    if isinstance(matcher, Extension):
        return matcher.matches(path)
    detected = detect_file_type(path)
    return matcher == detected


def is_valid_file_type(path: Path | str, allowed: AllowedSpec) -> bool:
    """Return ``True`` if *path* matches the provided type specification."""

    target = Path(path)
    matchers = _normalize_matchers(allowed)
    for matcher in matchers:
        if _match_extension_or_marker(target, matcher):
            return True
    return False


def _describe_matchers(matchers: Sequence[Extension | InputMarker[Any]]) -> str:
    labels: list[str] = []
    for matcher in matchers:
        if isinstance(matcher, Extension):
            labels.append(
                "Extensions(" + ", ".join(sorted(matcher.patterns)) + ")"
            )
        else:
            labels.append(matcher.name.capitalize())
    return " | ".join(dict.fromkeys(labels))


def validate_file_types(paths: Sequence[Path | str], allowed: AllowedSpec) -> tuple[Path, ...]:
    """Validate that every path in *paths* matches *allowed*.

    Returns the normalized tuple of ``Path`` objects when validation succeeds.
    Raises ``ValueError`` with a descriptive message otherwise.
    """

    normalized = tuple(Path(path) for path in paths)
    if not normalized:
        return tuple()

    matchers = _normalize_matchers(allowed)
    description = _describe_matchers(matchers)

    for path in normalized:
        if not any(_match_extension_or_marker(path, matcher) for matcher in matchers):
            msg = f"Path '{path}' does not satisfy required file types: {description}"
            raise ValueError(msg)
    return normalized


@contextmanager
def temp_directory(prefix: str | None = None) -> Iterator[Path]:
    """Return a context manager yielding a temporary directory as ``Path``."""

    with TemporaryDirectory(prefix=prefix) as temp_dir:
        yield Path(temp_dir)


def sanitize_filename(name: str, replacement: str = "_") -> str:
    """Produce a filesystem-friendly filename derived from *name*."""

    if not replacement:
        msg = "Replacement string must not be empty"
        raise ValueError(msg)

    normalized = unicodedata.normalize("NFKD", name)
    ascii_safe = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = _INVALID_FILENAME_PATTERN.sub(replacement, ascii_safe)
    cleaned = cleaned.strip(" .")
    cleaned = re.sub(rf"{re.escape(replacement)}{{2,}}", replacement, cleaned)

    if not cleaned:
        cleaned = "file"

    return cleaned[:255]


def safe_join(base: Path | str, *parts: Path | str) -> Path:
    """Safely join *parts* to *base*, ensuring the result stays within *base*."""

    base_path = Path(base).resolve()
    current = base_path
    for part in parts:
        current = current.joinpath(Path(part))
    resolved = current.resolve()
    try:
        resolved.relative_to(base_path)
    except ValueError as exc:
        msg = "Resulting path escapes the base directory"
        raise ValueError(msg) from exc
    return resolved
