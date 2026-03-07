from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pcontext.runtime.ipc_models import ShellContext


@dataclass(frozen=True, slots=True)
class SelectionEntry:
    """
    Нормализованный объект выбора.

    Внутри агента уже удобнее работать не со строками, а с Path
    и заранее вычисленным расширением.
    """

    path: Path
    entry_type: Literal["file", "folder"]
    extension: str | None


@dataclass(frozen=True, slots=True)
class InvocationContext:
    """
    Нормализованный контекст запуска.
    """

    source: Literal["selection", "background"]
    current_folder: Path | None
    entries: tuple[SelectionEntry, ...]

    def selected_paths(self) -> tuple[Path, ...]:
        """
        Возвращает только пути выбранных объектов.
        """
        return tuple(entry.path for entry in self.entries)


def _extract_extension(path: Path) -> str | None:
    """
    Возвращает расширение без точки в нижнем регистре.
    """
    suffix = path.suffix.strip().lower().lstrip(".")
    return suffix or None


def normalize_shell_context(context: ShellContext) -> InvocationContext:
    """
    Преобразует внешний shell-контекст в внутреннее представление агента.
    """
    normalized_entries: list[SelectionEntry] = []

    for entry in context.entries:
        path = Path(entry.path)
        normalized_entries.append(
            SelectionEntry(
                path=path,
                entry_type=entry.entry_type,
                extension=(
                    _extract_extension(path) if entry.entry_type == "file" else None
                ),
            )
        )

    current_folder = Path(context.current_folder) if context.current_folder else None

    if current_folder is None and normalized_entries:
        first_entry = normalized_entries[0]
        current_folder = first_entry.path.parent

    return InvocationContext(
        source=context.source,
        current_folder=current_folder,
        entries=tuple(normalized_entries),
    )
