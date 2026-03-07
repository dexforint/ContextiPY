from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal


SelectionKind = Literal[
    "file",
    "folder",
    "image",
    "video",
    "txt",
    "doc",
    "archive",
    "python",
    "exe",
    "current_folder",
    "extensions",
]

# Ниже лежат базовые наборы расширений.
# Они не являются окончательной логикой распознавания файлов.
# Это только декларативная схема, которую позже будет использовать движок фильтрации.
_IMAGE_EXTENSIONS = ("png", "jpg", "jpeg", "bmp", "webp", "gif", "tif", "tiff")
_VIDEO_EXTENSIONS = ("mp4", "mkv", "avi", "mov", "wmv", "webm", "m4v")
_TEXT_EXTENSIONS = (
    "txt",
    "md",
    "rst",
    "json",
    "yaml",
    "yml",
    "toml",
    "ini",
    "csv",
    "log",
)
_DOC_EXTENSIONS = ("pdf", "doc", "docx", "odt", "rtf")
_ARCHIVE_EXTENSIONS = ("zip", "7z", "rar", "tar", "gz", "bz2", "xz")
_PYTHON_EXTENSIONS = ("py", "pyw")
_EXE_EXTENSIONS = ("exe", "msi", "bat", "cmd", "com", "ps1", "sh", "appimage")


class SelectionExpression:
    """
    Базовый класс для выражений выбора.

    Он нужен для поддержки синтаксиса:
        Image() | Video()
    """

    def flatten(self) -> tuple["InputSpec", ...]:
        """
        Преобразует выражение в плоский список атомарных правил.
        """
        raise NotImplementedError

    def __or__(self, other: "SelectionExpression") -> "SelectionUnion":
        """
        Объединяет два правила через логическое "или".
        """
        return _build_selection_union(self, other)


@dataclass(frozen=True, slots=True)
class InputSpec(SelectionExpression):
    """
    Атомарное правило выбора.

    Примеры:
        File()
        Image()
        Extensions(["jpg", "png"])
    """

    kind: SelectionKind
    multiple: bool = False
    extensions: tuple[str, ...] = ()

    def flatten(self) -> tuple["InputSpec", ...]:
        return (self,)


@dataclass(frozen=True, slots=True)
class SelectionUnion(SelectionExpression):
    """
    Объединение нескольких правил выбора.

    Пример:
        Image() | Video()
    """

    members: tuple[InputSpec, ...]

    def __post_init__(self) -> None:
        if not self.members:
            raise ValueError("SelectionUnion не может быть пустым.")

    def flatten(self) -> tuple[InputSpec, ...]:
        return self.members


def _normalize_extensions(extensions: Iterable[str]) -> tuple[str, ...]:
    """
    Приводит расширения к единому виду.

    Мы удаляем ведущую точку, переводим строку в нижний регистр
    и убираем дубликаты с сохранением порядка.
    """
    normalized: list[str] = []

    for raw_value in extensions:
        value = raw_value.strip().lower().lstrip(".")
        if not value:
            raise ValueError("Расширение не может быть пустым.")
        normalized.append(value)

    return tuple(dict.fromkeys(normalized))


def _make_input(
    kind: SelectionKind,
    *,
    multiple: bool = False,
    extensions: Iterable[str] = (),
) -> InputSpec:
    """
    Создаёт атомарное правило выбора.
    """
    return InputSpec(
        kind=kind,
        multiple=multiple,
        extensions=_normalize_extensions(extensions),
    )


def _build_selection_union(
    left: SelectionExpression,
    right: SelectionExpression,
) -> SelectionUnion:
    """
    Объединяет два выражения в одно и убирает дубликаты.
    """
    combined = left.flatten() + right.flatten()
    unique_members = tuple(dict.fromkeys(combined))
    return SelectionUnion(members=unique_members)


def File() -> InputSpec:
    """Один любой файл."""
    return _make_input("file")


def Files() -> InputSpec:
    """Несколько любых файлов."""
    return _make_input("file", multiple=True)


def Folder() -> InputSpec:
    """Одна папка."""
    return _make_input("folder")


def Folders() -> InputSpec:
    """Несколько папок."""
    return _make_input("folder", multiple=True)


def CurrentFolder() -> InputSpec:
    """
    Текущая папка, в которой было открыто контекстное меню на пустой области.
    """
    return _make_input("current_folder")


def Image() -> InputSpec:
    """Одно изображение."""
    return _make_input("image", extensions=_IMAGE_EXTENSIONS)


def Images() -> InputSpec:
    """Несколько изображений."""
    return _make_input("image", multiple=True, extensions=_IMAGE_EXTENSIONS)


def Video() -> InputSpec:
    """Одно видео."""
    return _make_input("video", extensions=_VIDEO_EXTENSIONS)


def Videos() -> InputSpec:
    """Несколько видео."""
    return _make_input("video", multiple=True, extensions=_VIDEO_EXTENSIONS)


def TXT() -> InputSpec:
    """Один текстовый файл."""
    return _make_input("txt", extensions=_TEXT_EXTENSIONS)


def TXTs() -> InputSpec:
    """Несколько текстовых файлов."""
    return _make_input("txt", multiple=True, extensions=_TEXT_EXTENSIONS)


def DOC() -> InputSpec:
    """Один документ."""
    return _make_input("doc", extensions=_DOC_EXTENSIONS)


def DOCs() -> InputSpec:
    """Несколько документов."""
    return _make_input("doc", multiple=True, extensions=_DOC_EXTENSIONS)


def ARCHIVE() -> InputSpec:
    """Один архив."""
    return _make_input("archive", extensions=_ARCHIVE_EXTENSIONS)


def ARCHIVEs() -> InputSpec:
    """Несколько архивов."""
    return _make_input("archive", multiple=True, extensions=_ARCHIVE_EXTENSIONS)


def PYTHON() -> InputSpec:
    """Один Python-файл."""
    return _make_input("python", extensions=_PYTHON_EXTENSIONS)


def PYTHONs() -> InputSpec:
    """Несколько Python-файлов."""
    return _make_input("python", multiple=True, extensions=_PYTHON_EXTENSIONS)


def EXE() -> InputSpec:
    """Один исполняемый файл."""
    return _make_input("exe", extensions=_EXE_EXTENSIONS)


def EXEs() -> InputSpec:
    """Несколько исполняемых файлов."""
    return _make_input("exe", multiple=True, extensions=_EXE_EXTENSIONS)


def Extensions(extensions: Iterable[str], *, multiple: bool = False) -> InputSpec:
    """
    Пользовательский набор расширений.

    Пример:
        Extensions(["jpg", "png"])
    """
    normalized = _normalize_extensions(extensions)
    if not normalized:
        raise ValueError("Нужно указать хотя бы одно расширение.")

    return InputSpec(
        kind="extensions",
        multiple=multiple,
        extensions=normalized,
    )
