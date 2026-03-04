"""
pcontext.api — Публичный API для авторов скриптов.

Этот модуль экспортирует всё, что нужно пользователю при написании
скриптов для PContext:

  • Декораторы: oneshot_script, Service
  • Типы файлов: File, Folder, Image, Video, TXT, DOC, ARCHIVE, PYTHON, EXE
  • Множественные типы: Files, Folders, Images, Videos, TXTs, DOCs, ...
  • Пользовательские расширения: Extensions
  • Параметры: Param
"""

from __future__ import annotations

from pcontext.api.decorators import Service, oneshot_script
from pcontext.api.file_types import (
    ARCHIVE,
    ARCHIVES,
    DOC,
    DOCS,
    EXE,
    EXES,
    Extensions,
    File,
    Files,
    Folder,
    Folders,
    Image,
    Images,
    PYTHON,
    PYTHONS,
    TXT,
    TXTs,
    Video,
    Videos,
)
from pcontext.api.param import Param

__all__: list[str] = [
    # Декораторы
    "oneshot_script",
    "Service",
    # Параметры
    "Param",
    # Одиночные типы файлов
    "File",
    "Folder",
    "Image",
    "Video",
    "TXT",
    "DOC",
    "ARCHIVE",
    "PYTHON",
    "EXE",
    # Множественные типы файлов
    "Files",
    "Folders",
    "Images",
    "Videos",
    "TXTs",
    "DOCs",
    "ARCHIVES",
    "PYTHONS",
    "EXES",
    # Пользовательские расширения
    "Extensions",
]