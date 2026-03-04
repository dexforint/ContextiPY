"""
pcontext.api.file_types — Типы входных файлов для скриптов PContext.

Каждый тип представляет собой объект-маркер, который указывает,
какие файлы может принимать скрипт. Тип используется как значение
по умолчанию для параметра функции-скрипта:

    @oneshot_script(title="Мой скрипт")
    def my_script(path: str = Image()):
        ...

Поддерживаются:
  • Одиночные типы: File, Folder, Image, Video, TXT, DOC, ARCHIVE, PYTHON, EXE
  • Множественные типы: Files, Folders, Images, Videos, TXTs, DOCs, ...
  • Пользовательские расширения: Extensions(["jpg", "png"])
  • Объединение типов оператором |: Image() | Video()
"""

from __future__ import annotations

from pcontext.core.constants import (
    ARCHIVE_EXTENSIONS,
    DOC_EXTENSIONS,
    EXE_EXTENSIONS,
    IMAGE_EXTENSIONS,
    PYTHON_EXTENSIONS,
    TXT_EXTENSIONS,
    VIDEO_EXTENSIONS,
)


class FileType:
    """
    Базовый класс для всех типов файлов.

    Каждый экземпляр хранит:
      • name       — человекочитаемое имя типа ("Image", "Video", ...)
      • extensions — frozenset допустимых расширений ({".jpg", ".png", ...})
                     Пустой frozenset означает «любое расширение»
      • multiple   — True, если скрипт принимает несколько файлов
      • is_folder  — True, если тип представляет папку (не файл)

    Поддерживает оператор | для объединения типов:
        Image() | Video()  → FileType с расширениями изображений и видео
    """

    def __init__(
        self,
        name: str,
        extensions: frozenset[str],
        *,
        multiple: bool = False,
        is_folder: bool = False,
    ) -> None:
        self.name: str = name
        self.extensions: frozenset[str] = extensions
        self.multiple: bool = multiple
        self.is_folder: bool = is_folder

    def __or__(self, other: FileType) -> FileType:
        """
        Объединяет два типа файлов оператором |.

        Пример:
            Image() | Video()
            → FileType(name="Image | Video", extensions={".jpg", ".mp4", ...})

        Правила:
          • Расширения объединяются (union)
          • Если хотя бы один тип множественный, результат тоже множественный
          • Если хотя бы один тип — папка, is_folder устанавливается в True
          • Если оба набора расширений пусты (File | Folder), результат —
            любое расширение (пустой frozenset)
        """
        # Если один из типов принимает ВСЁ (пустой frozenset),
        # результат тоже принимает всё
        if not self.extensions or not other.extensions:
            merged_extensions = frozenset[str]()
        else:
            merged_extensions = self.extensions | other.extensions

        return FileType(
            name=f"{self.name} | {other.name}",
            extensions=merged_extensions,
            multiple=self.multiple or other.multiple,
            is_folder=self.is_folder or other.is_folder,
        )

    def __repr__(self) -> str:
        """Строковое представление для отладки."""
        suffix = " (multiple)" if self.multiple else ""
        suffix += " (folder)" if self.is_folder else ""
        return f"FileType({self.name}{suffix})"


# ═════════════════════════════════════════════════════════════════════════════
# Одиночные типы (скрипт получает ОДИН путь)
# ═════════════════════════════════════════════════════════════════════════════


class File(FileType):
    """Любой файл (без ограничения по расширению)."""

    def __init__(self) -> None:
        # Пустой frozenset = принимаем файлы с любым расширением
        super().__init__("File", frozenset())


class Folder(FileType):
    """Папка (директория)."""

    def __init__(self) -> None:
        super().__init__("Folder", frozenset(), is_folder=True)


class Image(FileType):
    """Файл изображения (.jpg, .png, .gif, ...)."""

    def __init__(self) -> None:
        super().__init__("Image", IMAGE_EXTENSIONS)


class Video(FileType):
    """Видеофайл (.mp4, .avi, .mkv, ...)."""

    def __init__(self) -> None:
        super().__init__("Video", VIDEO_EXTENSIONS)


class TXT(FileType):
    """Текстовый файл (.txt, .yaml, .json, .md, ...)."""

    def __init__(self) -> None:
        super().__init__("TXT", TXT_EXTENSIONS)


class DOC(FileType):
    """Документ (.pdf, .docx, .xlsx, ...)."""

    def __init__(self) -> None:
        super().__init__("DOC", DOC_EXTENSIONS)


class ARCHIVE(FileType):
    """Архив (.zip, .7z, .rar, .tar.gz, ...)."""

    def __init__(self) -> None:
        super().__init__("ARCHIVE", ARCHIVE_EXTENSIONS)


class PYTHON(FileType):
    """Python-файл (.py, .pyw, .pyi)."""

    def __init__(self) -> None:
        super().__init__("PYTHON", PYTHON_EXTENSIONS)


class EXE(FileType):
    """Исполняемый файл (.exe, .msi, .bat, ...)."""

    def __init__(self) -> None:
        super().__init__("EXE", EXE_EXTENSIONS)


# ═════════════════════════════════════════════════════════════════════════════
# Множественные типы (скрипт получает СПИСОК путей)
# ═════════════════════════════════════════════════════════════════════════════


class Files(FileType):
    """Несколько любых файлов."""

    def __init__(self) -> None:
        super().__init__("Files", frozenset(), multiple=True)


class Folders(FileType):
    """Несколько папок."""

    def __init__(self) -> None:
        super().__init__("Folders", frozenset(), multiple=True, is_folder=True)


class Images(FileType):
    """Несколько изображений."""

    def __init__(self) -> None:
        super().__init__("Images", IMAGE_EXTENSIONS, multiple=True)


class Videos(FileType):
    """Несколько видеофайлов."""

    def __init__(self) -> None:
        super().__init__("Videos", VIDEO_EXTENSIONS, multiple=True)


class TXTs(FileType):
    """Несколько текстовых файлов."""

    def __init__(self) -> None:
        super().__init__("TXTs", TXT_EXTENSIONS, multiple=True)


class DOCs(FileType):
    """Несколько документов."""

    def __init__(self) -> None:
        super().__init__("DOCs", DOC_EXTENSIONS, multiple=True)


class ARCHIVES(FileType):
    """Несколько архивов."""

    def __init__(self) -> None:
        super().__init__("ARCHIVES", ARCHIVE_EXTENSIONS, multiple=True)


class PYTHONS(FileType):
    """Несколько Python-файлов."""

    def __init__(self) -> None:
        super().__init__("PYTHONS", PYTHON_EXTENSIONS, multiple=True)


class EXES(FileType):
    """Несколько исполняемых файлов."""

    def __init__(self) -> None:
        super().__init__("EXES", EXE_EXTENSIONS, multiple=True)


# ═════════════════════════════════════════════════════════════════════════════
# Пользовательские расширения
# ═════════════════════════════════════════════════════════════════════════════


class Extensions(FileType):
    """
    Тип файлов с явно указанными расширениями.

    Пример:
        # Только .jpg и .png
        Extensions(["jpg", "png"])

        # Множественный выбор .csv файлов
        Extensions(["csv"], multiple=True)

    Args:
        extensions: Список расширений БЕЗ точки: ["jpg", "png"]
        multiple:   Принимать несколько файлов (по умолчанию — нет)
    """

    def __init__(
        self,
        extensions: list[str],
        *,
        multiple: bool = False,
    ) -> None:
        # Нормализуем: пользователь пишет "jpg", мы храним ".jpg"
        normalized = frozenset(
            ext if ext.startswith(".") else f".{ext}"
            for ext in extensions
        )

        # Формируем человекочитаемое имя: "Extensions(.jpg, .png)"
        sorted_exts = sorted(normalized)
        name = f"Extensions({', '.join(sorted_exts)})"

        super().__init__(name, normalized, multiple=multiple)