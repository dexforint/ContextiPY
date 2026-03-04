"""
pcontext.api.script_meta — Внутренние структуры метаданных скриптов.

Эти dataclass-ы НЕ являются частью публичного API. Они используются
ядром PContext для хранения разобранной информации о каждом скрипте
и сервисе после загрузки .py-файла.

Иерархия:
  ScriptMeta       — базовые метаданные (общие для oneshot и service)
  OneshotMeta      — метаданные одноразового скрипта
  ServiceScriptMeta — метаданные одного метода сервиса (@service.script)
  ServiceMeta      — метаданные сервиса (класс + его методы-скрипты)
  ParamMeta        — описание одного параметра
  FileInputMeta    — описание одного файлового входа
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from pcontext.api.file_types import FileType


@dataclass
class ParamMeta:
    """
    Метаданные одного настраиваемого параметра (Param).

    Собираются при парсинге декорированной функции/класса.
    """

    # Имя параметра в коде (например, "server_url")
    name: str

    # Тип параметра (str, int, float, bool, или Enum-подкласс)
    annotation: type

    # Значение по умолчанию
    default: Any

    # Ограничения для числовых типов
    ge: int | float | None = None
    le: int | float | None = None

    # Описание параметра (отображается в GUI)
    description: str = ""


@dataclass
class FileInputMeta:
    """
    Метаданные одного файлового входа скрипта.

    Например, если функция принимает:
        def my_script(image: str = Image()):
    то создаётся FileInputMeta с:
        param_name="image", file_type=Image()
    """

    # Имя параметра в коде (например, "image_path")
    param_name: str

    # Объект типа файла (Image, Video, File, Extensions, ...)
    file_type: FileType


@dataclass
class ScriptMeta:
    """
    Базовые метаданные, общие для oneshot-скриптов и методов сервисов.
    """

    # Уникальный идентификатор скрипта.
    # Если не указан пользователем — генерируется автоматически
    # из имени файла и имени функции.
    id: str

    # Название скрипта в контекстном меню
    title: str

    # Описание скрипта (отображается в GUI)
    description: str

    # Максимальное время выполнения (секунды). None = без ограничения.
    timeout: float | None

    # Путь до .ico-файла иконки (отображается в контекстном меню).
    # None = без иконки.
    icon_path: str | None

    # Список файловых входов (может быть пустым — скрипт без файлов)
    file_inputs: list[FileInputMeta] = field(default_factory=list)

    # Список настраиваемых параметров
    params: list[ParamMeta] = field(default_factory=list)

    # Группа в контекстном меню (определяется по подпапке).
    # Пример: "Analyze" для файла scripts/Analyze/analyze.py
    # Пустая строка = корень меню PContext.
    group: str = ""

    # Абсолютный путь к .py-файлу, содержащему скрипт
    source_file: str = ""


@dataclass
class OneshotMeta(ScriptMeta):
    """
    Метаданные одноразового скрипта (@oneshot_script).

    Содержит ссылку на саму функцию-обработчик.
    """

    # Ссылка на декорированную функцию
    handler: Callable[..., Any] | None = None


@dataclass
class ServiceScriptMeta(ScriptMeta):
    """
    Метаданные одного метода сервиса (@service.script).

    Хранит имя метода, чтобы при вызове найти его на экземпляре сервиса.
    """

    # Имя метода в классе сервиса (например, "detect")
    method_name: str = ""


@dataclass
class ServiceMeta:
    """
    Метаданные сервиса (декорированного класса).

    Сервис — долгоживущий объект, который инициализирует тяжёлые
    ресурсы (модели, подключения) и предоставляет методы-скрипты.
    """

    # Уникальный идентификатор сервиса
    id: str

    # Название сервиса (для отображения в GUI)
    title: str

    # Описание сервиса
    description: str

    # Максимальное время жизни сервиса (секунды). None = бесконечно.
    timeout: float | None

    # Максимальное время простоя (секунды). None = бесконечно.
    max_downtime: float | None

    # Запускать сервис автоматически при старте PContext
    on_startup: bool

    # Путь до .ico-иконки сервиса
    icon_path: str | None

    # Настраиваемые параметры сервиса (из __init__)
    params: list[ParamMeta] = field(default_factory=list)

    # Методы-скрипты сервиса (каждый — отдельный пункт контекстного меню)
    scripts: list[ServiceScriptMeta] = field(default_factory=list)

    # Ссылка на класс сервиса (для создания экземпляра)
    service_class: type | None = None

    # Группа в контекстном меню
    group: str = ""

    # Абсолютный путь к .py-файлу
    source_file: str = ""