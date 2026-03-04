"""
pcontext.__main__ — Точка входа приложения PContext.

Запуск из командной строки:
    python -m pcontext          # запуск основного приложения (tray + IPC-сервер)

При установке пакета через pip также доступна команда:
    pcontext                    # эквивалент python -m pcontext
"""

from __future__ import annotations


def main() -> None:
    """
    Главная функция запуска приложения PContext.

    Последовательность запуска:
      1. Создание директорий (~/.pcontext/scripts, config, logs, ...)
      2. Загрузка конфигурации и реестра скриптов
      3. Запуск IPC-сервера (приём команд из контекстного меню)
      4. Автозапуск сервисов, помеченных on_startup=True
      5. Запуск графического интерфейса (QSystemTrayIcon)
    """
    # Импорты внутри функции — чтобы при «import pcontext» в скриптах
    # пользователя не загружалось ядро приложения целиком
    from pcontext.core import ensure_directories
    from pcontext.core.constants import APP_NAME, APP_VERSION

    # Шаг 1: гарантируем, что все нужные папки существуют
    ensure_directories()

    # Информируем пользователя (временная заглушка, будет заменена на tray)
    print(f"{APP_NAME} v{APP_VERSION} — приложение запущено")

    # TODO (Этап 4):  Загрузка конфигурации, реестра скриптов, хранилища параметров
    # TODO (Этап 7):  Запуск IPC-сервера на localhost:19836
    # TODO (Этап 9):  Автозапуск сервисов (on_startup=True)
    # TODO (Этап 10): Запуск QApplication + QSystemTrayIcon + event loop


# Этот блок выполняется, когда пользователь запускает:
#   python -m pcontext
if __name__ == "__main__":
    main()