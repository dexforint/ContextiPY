from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pcontext.registrar.introspection import discover_python_files
from pcontext.registrar.models import (
    InputArgumentManifest,
    OneshotScriptManifest,
    ServiceManifest,
    ServiceScriptManifest,
)
from pcontext.registrar.subprocess_runner import inspect_script_file_in_subprocess
from pcontext.runtime.matching import ManifestMenuCommandDefinition


@dataclass(frozen=True, slots=True)
class CatalogFailure:
    """
    Ошибка анализа одного пользовательского файла.
    """

    source_file: str
    message: str


@dataclass(frozen=True, slots=True)
class AgentCatalog:
    """
    Полный снимок текущего каталога пользовательских скриптов.

    Здесь хранятся:
    - исходные манифесты;
    - список shell-команд, которые реально могут появляться в контекстном меню;
    - ошибки файлов, не прошедших анализ.
    """

    oneshot_scripts: tuple[OneshotScriptManifest, ...]
    services: tuple[ServiceManifest, ...]
    context_commands: tuple[ManifestMenuCommandDefinition, ...]
    failures: tuple[CatalogFailure, ...]

    @property
    def service_ids(self) -> tuple[str, ...]:
        """
        Возвращает идентификаторы всех известных сервисов.
        """
        return tuple(service.id for service in self.services)


def _select_single_context_input(
    inputs: list[InputArgumentManifest],
    *,
    owner_id: str,
) -> tuple[tuple[object, ...] | None, str | None]:
    """
    Выбирает единственный input-аргумент, который можно привязать к shell-контексту.

    На текущем этапе мы поддерживаем только два случая:
    - входов нет: такой скрипт доступен для прямого запуска из UI, но не из shell-меню;
    - вход ровно один: его правила используются для контекстного меню.

    Если входов несколько, такой сценарий пока пропускается как неоднозначный.
    """
    if not inputs:
        return None, None

    if len(inputs) > 1:
        return None, (
            f"Сущность '{owner_id}' содержит несколько входных аргументов. "
            "На текущем этапе shell-меню поддерживает только один входной аргумент."
        )

    selected_input = inputs[0]
    return tuple(selected_input.rules), None


def _make_oneshot_context_command(
    manifest: OneshotScriptManifest,
) -> tuple[ManifestMenuCommandDefinition | None, str | None]:
    """
    Преобразует oneshot-манифест в shell-команду, если это возможно.
    """
    rules, error_message = _select_single_context_input(
        manifest.inputs,
        owner_id=manifest.id,
    )
    if error_message is not None:
        return None, error_message

    if rules is None:
        return None, None

    return (
        ManifestMenuCommandDefinition(
            id=manifest.id,
            title=manifest.title,
            input_rules=rules,
            service_id=None,
            icon=manifest.icon,
        ),
        None,
    )


def _make_service_context_command(
    service: ServiceManifest,
    method: ServiceScriptManifest,
) -> tuple[ManifestMenuCommandDefinition | None, str | None]:
    """
    Преобразует метод сервиса в shell-команду, если это возможно.
    """
    rules, error_message = _select_single_context_input(
        method.inputs,
        owner_id=method.id,
    )
    if error_message is not None:
        return None, error_message

    if rules is None:
        return None, None

    return (
        ManifestMenuCommandDefinition(
            id=method.id,
            title=method.title,
            input_rules=rules,
            service_id=service.id,
            icon=method.icon,
        ),
        None,
    )


def load_agent_catalog(scripts_root: Path) -> AgentCatalog:
    """
    Загружает живой каталог пользовательских скриптов.

    Ошибка в одном файле не должна ломать весь каталог, поэтому каждый файл
    анализируется отдельно, а ошибки собираются в список `failures`.
    """
    resolved_scripts_root = scripts_root.expanduser().resolve()

    oneshot_scripts: list[OneshotScriptManifest] = []
    services: list[ServiceManifest] = []
    context_commands: list[ManifestMenuCommandDefinition] = []
    failures: list[CatalogFailure] = []

    for file_path in discover_python_files(resolved_scripts_root):
        try:
            module_result = inspect_script_file_in_subprocess(
                file_path,
                scripts_root=resolved_scripts_root,
            )
        except Exception as error:  # noqa: BLE001
            failures.append(
                CatalogFailure(
                    source_file=str(file_path.resolve()),
                    message=str(error),
                )
            )
            continue

        oneshot_scripts.extend(module_result.oneshot_scripts)
        services.extend(module_result.services)

        for script_manifest in module_result.oneshot_scripts:
            command, error_message = _make_oneshot_context_command(script_manifest)
            if error_message is not None:
                failures.append(
                    CatalogFailure(
                        source_file=script_manifest.source_file,
                        message=error_message,
                    )
                )
                continue

            if command is not None:
                context_commands.append(command)

        for service_manifest in module_result.services:
            for method_manifest in service_manifest.scripts:
                command, error_message = _make_service_context_command(
                    service_manifest,
                    method_manifest,
                )
                if error_message is not None:
                    failures.append(
                        CatalogFailure(
                            source_file=method_manifest.source_file,
                            message=error_message,
                        )
                    )
                    continue

                if command is not None:
                    context_commands.append(command)

    sorted_oneshots = tuple(
        sorted(oneshot_scripts, key=lambda item: (item.title.lower(), item.id))
    )
    sorted_services = tuple(
        sorted(services, key=lambda item: (item.title.lower(), item.id))
    )
    sorted_commands = tuple(
        sorted(context_commands, key=lambda item: (item.title.lower(), item.id))
    )
    sorted_failures = tuple(
        sorted(failures, key=lambda item: (item.source_file, item.message))
    )

    return AgentCatalog(
        oneshot_scripts=sorted_oneshots,
        services=sorted_services,
        context_commands=sorted_commands,
        failures=sorted_failures,
    )
