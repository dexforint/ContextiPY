"""
PContext — библиотека для интеграции Python-скриптов в контекстное меню ОС.

Позволяет пользователям:
  • Писать Python-скрипты с декораторами (@oneshot_script, Service)
  • Регистрировать их в контекстном меню операционной системы
  • Запускать скрипты правым кликом по файлам / папкам / пустой области
  • Управлять долгоживущими сервисами через tray-иконку
  • Настраивать параметры скриптов без редактирования кода

Пример использования:
    from pcontext import oneshot_script, File, Param
    from pcontext.actions import Copy

    @oneshot_script(title="Мой скрипт")
    def my_script(file_path: str = File()):
        return Copy("Готово!")
"""

from __future__ import annotations

from pcontext.api import (
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
    Param,
    PYTHON,
    PYTHONS,
    Service,
    TXT,
    TXTs,
    Video,
    Videos,
    oneshot_script,
)
from pcontext.core.constants import APP_VERSION

__version__: str = APP_VERSION

__all__: list[str] = [
    "__version__",
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