"""
pcontext.api.decorators — Декораторы для регистрации скриптов и сервисов.

Основные элементы:
  • oneshot_script — декоратор для одноразовых скриптов
  • Service        — класс для создания долгоживущих сервисов

При декорировании функция/класс получает атрибут __pcontext_meta__,
который содержит разобранные метаданные (OneshotMeta / ServiceMeta).
Загрузчик скриптов (script_loader, Этап 4) будет искать этот атрибут
при импорте .py-файлов.
"""

from __future__ import annotations

import hashlib
import inspect
from typing import Any, Callable, TypeVar, overload

from pcontext.api.file_types import FileType
from pcontext.api.param import Param
from pcontext.api.script_meta import (
    FileInputMeta,
    OneshotMeta,
    ParamMeta,
    ServiceMeta,
    ServiceScriptMeta,
)

# TypeVar для сохранения типа декорируемой функции
F = TypeVar("F", bound=Callable[..., Any])


# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные функции
# ═════════════════════════════════════════════════════════════════════════════


def _generate_id(name: str, source: str = "") -> str:
    """
    Генерирует уникальный ID скрипта из имени функции и исходного файла.

    Берёт первые 8 символов SHA-256 от строки «source:name».
    Пример: "upload_abc12345"

    Args:
        name:   Имя функции или класса.
        source: Путь к .py-файлу (может быть пуст).

    Returns:
        Строковый идентификатор вида "name_hash".
    """
    raw = f"{source}:{name}"
    hash_suffix = hashlib.sha256(raw.encode()).hexdigest()[:8]
    return f"{name}_{hash_suffix}"


def _parse_function_inputs(
    func: Callable[..., Any],
    *,
    skip_self: bool = False,
) -> tuple[list[FileInputMeta], list[ParamMeta]]:
    """
    Анализирует сигнатуру функции и разделяет параметры на:
      • Файловые входы (значение по умолчанию — экземпляр FileType)
      • Настраиваемые параметры (значение по умолчанию — экземпляр Param)

    Параметры без значения по умолчанию игнорируются (они будут переданы
    как позиционные аргументы при вызове).

    Args:
        func:      Анализируемая функция.
        skip_self: Пропустить параметр «self» (для методов класса).

    Returns:
        Кортеж (file_inputs, params).
    """
    sig = inspect.signature(func)
    file_inputs: list[FileInputMeta] = []
    params: list[ParamMeta] = []

    for param_name, param in sig.parameters.items():
        # Пропускаем «self» для методов класса
        if skip_self and param_name == "self":
            continue

        default = param.default

        # Параметр без значения по умолчанию — пропускаем
        if default is inspect.Parameter.empty:
            continue

        # --- Файловый вход ---
        if isinstance(default, FileType):
            file_inputs.append(
                FileInputMeta(
                    param_name=param_name,
                    file_type=default,
                )
            )
            continue

        # --- Настраиваемый параметр ---
        if isinstance(default, Param):
            # Определяем тип из аннотации (если есть)
            annotation = param.annotation
            if annotation is inspect.Parameter.empty:
                annotation = type(default.default)

            params.append(
                ParamMeta(
                    name=param_name,
                    annotation=annotation,
                    default=default.default,
                    ge=default.ge,
                    le=default.le,
                    description=default.description,
                )
            )
            continue

    return file_inputs, params


# ═════════════════════════════════════════════════════════════════════════════
# Декоратор oneshot_script
# ═════════════════════════════════════════════════════════════════════════════


def oneshot_script(
    *,
    title: str,
    description: str = "",
    timeout: float | None = None,
    icon_path: str | None = None,
    id: str | None = None,
) -> Callable[[F], F]:
    """
    Декоратор для регистрации одноразового скрипта.

    Помечает функцию как oneshot-скрипт PContext. При загрузке .py-файла
    загрузчик найдёт атрибут __pcontext_meta__ и зарегистрирует скрипт.

    Args:
        title:       Название в контекстном меню (обязательно).
        description: Описание скрипта (для GUI).
        timeout:     Максимальное время выполнения (секунды).
        icon_path:   Путь к .ico-файлу иконки.
        id:          Уникальный ID. Если None — генерируется автоматически.

    Пример:
        @oneshot_script(title="Загрузить файл", timeout=60)
        def upload(file_path: str = File()):
            ...
    """

    def decorator(func: F) -> F:
        # Разбираем параметры функции на файловые входы и Param-параметры
        file_inputs, params = _parse_function_inputs(func)

        # Генерируем ID, если не указан
        script_id = id if id is not None else _generate_id(func.__name__)

        # Создаём объект метаданных
        meta = OneshotMeta(
            id=script_id,
            title=title,
            description=description,
            timeout=timeout,
            icon_path=icon_path,
            file_inputs=file_inputs,
            params=params,
            handler=func,
        )

        # Сохраняем метаданные как атрибут функции.
        # Загрузчик скриптов будет искать именно этот атрибут.
        func.__pcontext_meta__ = meta  # type: ignore[attr-defined]

        return func

    return decorator


# ═════════════════════════════════════════════════════════════════════════════
# Класс Service
# ═════════════════════════════════════════════════════════════════════════════


class _ServiceScriptDecorator:
    """
    Декоратор @service.script(...) для методов класса сервиса.

    Не используется напрямую пользователем — вызывается через
    экземпляр Service().
    """

    def __init__(
        self,
        *,
        title: str,
        description: str = "",
        timeout: float | None = None,
        icon_path: str | None = None,
        id: str | None = None,
    ) -> None:
        self.title = title
        self.description = description
        self.timeout = timeout
        self.icon_path = icon_path
        self.id = id

    def __call__(self, method: F) -> F:
        """
        Декорирует метод класса сервиса.

        Сохраняет метаданные метода в атрибуте __pcontext_script_meta__.
        Позже, при декорировании класса через @service(...),
        эти метаданные собираются воедино.
        """
        # Разбираем параметры метода (skip_self=True — пропускаем self)
        file_inputs, params = _parse_function_inputs(method, skip_self=True)

        script_id = (
            self.id
            if self.id is not None
            else _generate_id(method.__name__)
        )

        meta = ServiceScriptMeta(
            id=script_id,
            title=self.title,
            description=self.description,
            timeout=self.timeout,
            icon_path=self.icon_path,
            file_inputs=file_inputs,
            params=params,
            method_name=method.__name__,
        )

        # Сохраняем метаданные метода
        method.__pcontext_script_meta__ = meta  # type: ignore[attr-defined]

        return method


class Service:
    """
    Фабрика для создания долгоживущих сервисов PContext.

    Использование:
        service = Service()

        @service(title="Yolo Detector", ...)
        class YoloDetector:
            def __init__(self, model: ModelName = Param("yolov8n.pt")):
                self.model = YOLO(model)

            @service.script(title="Detect objects")
            def detect(self, image: str = Image()):
                ...

    Важно: один экземпляр Service() соответствует одному сервису.
    Если в файле несколько сервисов, нужно создать несколько экземпляров.
    """

    def __init__(self) -> None:
        # Мета-данные сервиса заполняются при вызове @service(...)
        self._meta: ServiceMeta | None = None

    def script(
        self,
        *,
        title: str,
        description: str = "",
        timeout: float | None = None,
        icon_path: str | None = None,
        id: str | None = None,
    ) -> _ServiceScriptDecorator:
        """
        Декоратор для методов класса сервиса.

        Помечает метод как скрипт, доступный из контекстного меню.
        Скрипт виден в меню только когда сервис запущен.

        Args:
            title:       Название в контекстном меню.
            description: Описание (для GUI).
            timeout:     Максимальное время выполнения.
            icon_path:   Путь к .ico-иконке.
            id:          Уникальный ID.
        """
        return _ServiceScriptDecorator(
            title=title,
            description=description,
            timeout=timeout,
            icon_path=icon_path,
            id=id,
        )

    def __call__(
        self,
        *,
        title: str,
        description: str = "",
        timeout: float | None = None,
        max_downtime: float | None = None,
        on_startup: bool = False,
        icon_path: str | None = None,
        id: str | None = None,
    ) -> Callable[[type], type]:
        """
        Декоратор для класса сервиса.

        Собирает метаданные класса и его методов, помеченных
        @service.script(), в единый объект ServiceMeta.

        Args:
            title:        Название сервиса.
            description:  Описание.
            timeout:      Максимальное время жизни сервиса (секунды).
            max_downtime: Максимальное время простоя (секунды).
            on_startup:   Автозапуск при старте PContext.
            icon_path:    Путь к .ico-иконке.
            id:           Уникальный ID.
        """

        def decorator(cls: type) -> type:
            # Собираем метаданные методов-скриптов (@service.script)
            scripts: list[ServiceScriptMeta] = []

            for attr_name in dir(cls):
                # Пропускаем магические методы
                if attr_name.startswith("__"):
                    continue

                attr = getattr(cls, attr_name, None)
                if attr is None:
                    continue

                # Ищем атрибут __pcontext_script_meta__, установленный
                # декоратором @service.script()
                script_meta = getattr(attr, "__pcontext_script_meta__", None)
                if isinstance(script_meta, ServiceScriptMeta):
                    scripts.append(script_meta)

            # Разбираем параметры __init__ (skip_self=True)
            init_method = getattr(cls, "__init__", None)
            if init_method is not None:
                _, params = _parse_function_inputs(
                    init_method, skip_self=True
                )
            else:
                params = []

            service_id = (
                id if id is not None else _generate_id(cls.__name__)
            )

            # Создаём полный объект метаданных сервиса
            meta = ServiceMeta(
                id=service_id,
                title=title,
                description=description,
                timeout=timeout,
                max_downtime=max_downtime,
                on_startup=on_startup,
                icon_path=icon_path,
                params=params,
                scripts=scripts,
                service_class=cls,
            )

            # Сохраняем метаданные на классе
            cls.__pcontext_meta__ = meta  # type: ignore[attr-defined]

            # Сохраняем ссылку на мета в экземпляре Service
            self._meta = meta

            return cls

        return decorator