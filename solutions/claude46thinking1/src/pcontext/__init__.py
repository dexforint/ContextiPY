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

# Импортируем версию из единого источника правды (constants.py),
# чтобы не дублировать номер версии в нескольких местах
from pcontext.core.constants import APP_VERSION

# Версия пакета — доступна через pcontext.__version__
__version__: str = APP_VERSION

# Список имён, которые экспортируются при «from pcontext import *».
# По мере разработки сюда добавятся: oneshot_script, Service, Param,
# File, Folder, Image, Video, TXT, DOC, ARCHIVE, PYTHON, EXE,
# Images, Videos, Extensions и т.д.
__all__: list[str] = [
    "__version__",
]