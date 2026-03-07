from __future__ import annotations

import ast
import hashlib
import importlib.util
import inspect
import sys
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import Any, Annotated, get_args, get_origin, get_type_hints

from pcontext.metadata import (
    OneshotScriptOptions,
    ServiceOptions,
    ServiceScriptOptions,
)
from pcontext.registrar.models import (
    InputArgumentManifest,
    InputRuleManifest,
    ModuleInspectionResult,
    OneshotScriptManifest,
    ParamArgumentManifest,
    ServiceManifest,
    ServiceScriptManifest,
    ValueTypeManifest,
)
from pcontext.sdk.decorators import get_definition, get_service_binder_token
from pcontext.sdk.inputs import InputSpec, SelectionExpression
from pcontext.sdk.params import ParamSpec


def discover_python_files(scripts_root: Path) -> list[Path]:
    """
    Находит все Python-файлы в папке пользовательских скриптов.

    Мы рекурсивно обходим дерево, потому что пользователь может
    организовать свои скрипты по подпапкам.
    """
    return sorted(path for path in scripts_root.rglob("*.py") if path.is_file())


def compute_file_sha256(file_path: Path) -> str:
    """
    Считает SHA-256 хэш файла.

    Этот хэш позже пригодится для понимания, изменился ли скрипт
    и нужно ли его перерегистрировать.
    """
    digest = hashlib.sha256()
    with file_path.open("rb") as file:
        while True:
            chunk = file.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def extract_dependencies_from_module_docstring(file_path: Path) -> list[str]:
    """
    Читает верхний docstring модуля и трактует его как список зависимостей.

    Поведение намеренно простое:
    каждая непустая строка, не начинающаяся с `#`, считается строкой
    в формате requirements.txt.
    """
    source_text = file_path.read_text(encoding="utf-8")
    module_ast = ast.parse(source_text, filename=str(file_path))
    module_docstring = ast.get_docstring(module_ast, clean=False)

    if not module_docstring:
        return []

    dependencies: list[str] = []

    for raw_line in module_docstring.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        dependencies.append(line)

    return dependencies


def make_stable_definition_id(
    *,
    explicit_id: str | None,
    relative_path: str,
    qualname: str,
) -> str:
    """
    Создаёт стабильный идентификатор сущности.

    Если пользователь явно указал `id=...`, используем его.
    Иначе строим id из относительного пути и полного qualname.
    """
    if explicit_id is not None:
        return explicit_id

    payload = f"{relative_path}:{qualname}".encode("utf-8")
    digest = hashlib.sha1(payload).hexdigest()[:16]
    return f"auto:{digest}"


def _make_jsonable(value: Any) -> Any:
    """
    Приводит произвольное Python-значение к JSON-совместимому виду.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, Enum):
        return _make_jsonable(value.value)

    if isinstance(value, (list, tuple, set)):
        return [_make_jsonable(item) for item in value]

    if isinstance(value, dict):
        return {str(key): _make_jsonable(item) for key, item in value.items()}

    return repr(value)


def _display_type_name(annotation: Any) -> str:
    """
    Возвращает удобочитаемое имя типа.
    """
    if annotation is str:
        return "str"
    if annotation is int:
        return "int"
    if annotation is float:
        return "float"
    if annotation is bool:
        return "bool"
    if annotation is Path:
        return "pathlib.Path"

    if inspect.isclass(annotation):
        return f"{annotation.__module__}.{annotation.__qualname__}"

    return repr(annotation)


def describe_value_type(annotation: Any) -> ValueTypeManifest:
    """
    Преобразует Python-аннотацию в компактное описание типа.
    """
    origin = get_origin(annotation)

    if annotation is str:
        return ValueTypeManifest(kind="str", display_name="str")
    if annotation is int:
        return ValueTypeManifest(kind="int", display_name="int")
    if annotation is float:
        return ValueTypeManifest(kind="float", display_name="float")
    if annotation is bool:
        return ValueTypeManifest(kind="bool", display_name="bool")
    if annotation is Path:
        return ValueTypeManifest(kind="path", display_name="pathlib.Path")

    if inspect.isclass(annotation) and issubclass(annotation, Enum):
        return ValueTypeManifest(
            kind="enum",
            display_name=_display_type_name(annotation),
            enum_values=[_make_jsonable(member.value) for member in annotation],
        )

    if origin is list:
        return ValueTypeManifest(
            kind="list", display_name=_display_type_name(annotation)
        )

    return ValueTypeManifest(
        kind="unknown", display_name=_display_type_name(annotation)
    )


def _unwrap_annotated(annotation: Any) -> tuple[Any, list[Any]]:
    """
    Разворачивает `Annotated[T, ...]`.

    Если аннотация не является `Annotated`, возвращаем её как есть.
    """
    if get_origin(annotation) is Annotated:
        args = list(get_args(annotation))
        return args[0], args[1:]

    return annotation, []


def _extract_binding_metadata(
    parameter_name: str, annotation: Any
) -> tuple[Any, SelectionExpression | None, ParamSpec | None]:
    """
    Извлекает из аннотации базовый тип и PContext-метаданные.

    Мы поддерживаем только один input-binding и только один Param(...) на параметр.
    """
    base_annotation, metadata_items = _unwrap_annotated(annotation)

    input_binding: SelectionExpression | None = None
    param_binding: ParamSpec | None = None

    for metadata_item in metadata_items:
        if isinstance(metadata_item, SelectionExpression):
            if input_binding is not None:
                raise ValueError(
                    f"Параметр '{parameter_name}' содержит больше одного input-описания."
                )
            input_binding = metadata_item
            continue

        if isinstance(metadata_item, ParamSpec):
            if param_binding is not None:
                raise ValueError(
                    f"Параметр '{parameter_name}' содержит больше одного Param(...)."
                )
            param_binding = metadata_item

    if input_binding is not None and param_binding is not None:
        raise ValueError(
            f"Параметр '{parameter_name}' не может одновременно быть входом и настройкой."
        )

    return base_annotation, input_binding, param_binding


def _make_input_rules(expression: SelectionExpression) -> list[InputRuleManifest]:
    """
    Преобразует выражение выбора в список атомарных правил.
    """
    rules: list[InputRuleManifest] = []

    for spec in expression.flatten():
        if not isinstance(spec, InputSpec):
            raise TypeError("Обнаружено неподдерживаемое правило выбора.")

        rules.append(
            InputRuleManifest(
                kind=spec.kind,
                multiple=spec.multiple,
                extensions=list(spec.extensions),
            )
        )

    return rules


def _build_function_bindings(
    callable_object: Any,
    *,
    skip_self: bool,
    allow_inputs: bool,
) -> tuple[list[InputArgumentManifest], list[ParamArgumentManifest]]:
    """
    Анализирует параметры функции, метода или `__init__`.

    Возвращает два списка:
    - входные аргументы, влияющие на видимость пункта в контекстном меню;
    - настраиваемые параметры, сохраняемые в состоянии приложения.
    """
    signature = inspect.signature(callable_object)
    type_hints = get_type_hints(callable_object, include_extras=True)

    inputs: list[InputArgumentManifest] = []
    params: list[ParamArgumentManifest] = []

    for parameter_name, parameter in signature.parameters.items():
        if skip_self and parameter_name in {"self", "cls"}:
            continue

        if parameter.kind in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            raise ValueError(
                f"Параметр '{parameter_name}' использует *args/**kwargs, это не поддерживается."
            )

        annotation = type_hints.get(parameter_name, parameter.annotation)
        if annotation is inspect.Signature.empty:
            raise ValueError(
                f"У параметра '{parameter_name}' отсутствует аннотация типа."
            )

        base_annotation, input_binding, param_binding = _extract_binding_metadata(
            parameter_name,
            annotation,
        )

        if input_binding is None and param_binding is None:
            raise ValueError(
                f"Параметр '{parameter_name}' не содержит ни Input, ни Param(...)."
            )

        if input_binding is not None:
            if not allow_inputs:
                raise ValueError(
                    f"Параметр '{parameter_name}' не может быть входным в этом контексте."
                )

            inputs.append(
                InputArgumentManifest(
                    name=parameter_name,
                    value_type=describe_value_type(base_annotation),
                    rules=_make_input_rules(input_binding),
                )
            )
            continue

        if param_binding is None:
            raise RuntimeError("Внутренняя ошибка анализа параметров.")

        params.append(
            ParamArgumentManifest(
                name=parameter_name,
                value_type=describe_value_type(base_annotation),
                default=_make_jsonable(param_binding.default),
                title=param_binding.title,
                description=param_binding.description,
                ge=param_binding.ge,
                gt=param_binding.gt,
                le=param_binding.le,
                lt=param_binding.lt,
                min_length=param_binding.min_length,
                max_length=param_binding.max_length,
                pattern=param_binding.pattern,
            )
        )

    return inputs, params


def import_module_from_path(file_path: Path, *, scripts_root: Path) -> ModuleType:
    """
    Импортирует пользовательский модуль по абсолютному пути.

    В `sys.path` временно добавляется корень папки scripts,
    чтобы основные скрипты могли импортировать вспомогательные модули.
    """
    module_name_hash = hashlib.sha1(str(file_path).encode("utf-8")).hexdigest()
    module_name = f"_pcontext_user_{module_name_hash}"

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Не удалось создать spec для файла: {file_path}")

    module = importlib.util.module_from_spec(spec)

    scripts_root_str = str(scripts_root)
    added_to_sys_path = False

    if scripts_root_str not in sys.path:
        sys.path.insert(0, scripts_root_str)
        added_to_sys_path = True

    try:
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(module_name, None)
        if added_to_sys_path:
            try:
                sys.path.remove(scripts_root_str)
            except ValueError:
                pass

    return module


def _relative_path(file_path: Path, scripts_root: Path) -> str:
    """
    Возвращает путь файла относительно scripts_root.
    """
    return str(file_path.relative_to(scripts_root)).replace("\\", "/")


def _extract_oneshot_manifest(
    function: Any,
    *,
    file_path: Path,
    relative_path: str,
) -> OneshotScriptManifest:
    """
    Строит манифест для обычного одноразового скрипта.
    """
    definition = get_definition(function)
    if definition is None or definition.kind != "oneshot_script":
        raise ValueError("Ожидался объект oneshot_script.")

    options = definition.options
    if not isinstance(options, OneshotScriptOptions):
        raise TypeError("Для oneshot_script получен неверный тип опций.")

    inputs, params = _build_function_bindings(
        function,
        skip_self=False,
        allow_inputs=True,
    )

    script_id = make_stable_definition_id(
        explicit_id=options.id,
        relative_path=relative_path,
        qualname=function.__qualname__,
    )

    return OneshotScriptManifest(
        id=script_id,
        explicit_id=options.id,
        source_file=str(file_path),
        relative_path=relative_path,
        qualname=function.__qualname__,
        title=options.title,
        description=options.description,
        icon=options.icon,
        timeout=options.timeout,
        inputs=inputs,
        params=params,
        supports_direct_run=not inputs,
    )


def _extract_service_script_manifest(
    method: Any,
    *,
    service_id: str,
    service_qualname: str,
    file_path: Path,
    relative_path: str,
) -> ServiceScriptManifest:
    """
    Строит манифест для метода сервиса.
    """
    definition = get_definition(method)
    if definition is None or definition.kind != "service_script":
        raise ValueError("Ожидался объект service_script.")

    options = definition.options
    if not isinstance(options, ServiceScriptOptions):
        raise TypeError("Для service_script получен неверный тип опций.")

    inputs, params = _build_function_bindings(
        method,
        skip_self=True,
        allow_inputs=True,
    )

    script_id = make_stable_definition_id(
        explicit_id=options.id,
        relative_path=relative_path,
        qualname=method.__qualname__,
    )

    return ServiceScriptManifest(
        id=script_id,
        explicit_id=options.id,
        service_id=service_id,
        service_qualname=service_qualname,
        source_file=str(file_path),
        relative_path=relative_path,
        qualname=method.__qualname__,
        method_name=method.__name__,
        title=options.title,
        description=options.description,
        icon=options.icon,
        timeout=options.timeout,
        inputs=inputs,
        params=params,
        supports_direct_run=not inputs,
    )


def _extract_service_manifest(
    service_class: type[Any],
    *,
    file_path: Path,
    relative_path: str,
) -> ServiceManifest:
    """
    Строит манифест сервиса вместе со списком его script-методов.
    """
    definition = get_definition(service_class)
    if definition is None or definition.kind != "service":
        raise ValueError("Ожидался объект service.")

    options = definition.options
    if not isinstance(options, ServiceOptions):
        raise TypeError("Для service получен неверный тип опций.")

    if service_class.__init__ is object.__init__:
        init_params: list[ParamArgumentManifest] = []
    else:
        _, init_params = _build_function_bindings(
            service_class.__init__,
            skip_self=True,
            allow_inputs=False,
        )

    service_id = make_stable_definition_id(
        explicit_id=options.id,
        relative_path=relative_path,
        qualname=service_class.__qualname__,
    )

    binder_token = get_service_binder_token(service_class)
    service_scripts: list[ServiceScriptManifest] = []

    for _, member in service_class.__dict__.items():
        member_definition = get_definition(member)
        if member_definition is None or member_definition.kind != "service_script":
            continue

        if get_service_binder_token(member) != binder_token:
            continue

        service_scripts.append(
            _extract_service_script_manifest(
                member,
                service_id=service_id,
                service_qualname=service_class.__qualname__,
                file_path=file_path,
                relative_path=relative_path,
            )
        )

    return ServiceManifest(
        id=service_id,
        explicit_id=options.id,
        source_file=str(file_path),
        relative_path=relative_path,
        qualname=service_class.__qualname__,
        title=options.title,
        description=options.description,
        icon=options.icon,
        timeout=options.timeout,
        max_downtime=options.max_downtime,
        on_startup=options.on_startup,
        init_params=init_params,
        scripts=service_scripts,
    )


def inspect_script_file(
    file_path: Path, *, scripts_root: Path
) -> ModuleInspectionResult:
    """
    Полностью анализирует один Python-файл из scripts_root.

    Этот метод:
    - читает зависимости из docstring;
    - импортирует модуль;
    - ищет oneshot-скрипты и сервисы;
    - строит JSON-совместимый манифест.
    """
    absolute_file_path = file_path.resolve()
    absolute_scripts_root = scripts_root.resolve()
    relative_path = _relative_path(absolute_file_path, absolute_scripts_root)
    file_hash = compute_file_sha256(absolute_file_path)
    dependencies = extract_dependencies_from_module_docstring(absolute_file_path)

    module = import_module_from_path(
        absolute_file_path,
        scripts_root=absolute_scripts_root,
    )

    oneshot_scripts: list[OneshotScriptManifest] = []
    services: list[ServiceManifest] = []

    for _, member in inspect.getmembers(module):
        definition = get_definition(member)
        if definition is None:
            continue

        if definition.kind == "oneshot_script":
            oneshot_scripts.append(
                _extract_oneshot_manifest(
                    member,
                    file_path=absolute_file_path,
                    relative_path=relative_path,
                )
            )
            continue

        if definition.kind == "service" and inspect.isclass(member):
            services.append(
                _extract_service_manifest(
                    member,
                    file_path=absolute_file_path,
                    relative_path=relative_path,
                )
            )

    return ModuleInspectionResult(
        source_file=str(absolute_file_path),
        relative_path=relative_path,
        file_hash_sha256=file_hash,
        dependencies=dependencies,
        oneshot_scripts=oneshot_scripts,
        services=services,
    )
