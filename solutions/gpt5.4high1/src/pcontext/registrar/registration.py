from __future__ import annotations

from dataclasses import dataclass

from pcontext.config import PContextPaths, ensure_directories
from pcontext.registrar.introspection import (
    compute_file_sha256,
    discover_python_files,
    extract_dependencies_from_module_docstring,
)
from pcontext.registrar.subprocess_runner import inspect_script_file_in_subprocess
from pcontext.registrar.venv_manager import ensure_shared_venv, install_requirements
from pcontext.storage.state import StateStore


@dataclass(frozen=True, slots=True)
class RegistrationResult:
    """
    Сводка после выполнения команды регистрации.
    """

    processed_files: int
    changed_files: int
    unchanged_files: int
    removed_files: int
    failed_files: int
    installed_dependency_groups: int
    venv_created: bool


def _relative_path(source_file: str, scripts_root: str) -> str:
    """
    Возвращает относительный путь в унифицированном виде.
    """
    from pathlib import Path

    return str(
        Path(source_file).resolve().relative_to(Path(scripts_root).resolve())
    ).replace("\\", "/")


def register_scripts(
    paths: PContextPaths,
    *,
    state_store: StateStore | None = None,
) -> RegistrationResult:
    """
    Выполняет регистрацию пользовательских скриптов PContext.

    Что делает регистрация:
    - создаёт общее venv;
    - ищет новые и изменённые `.py` файлы в папке scripts;
    - устанавливает зависимости из верхнего docstring;
    - проверяет, что модуль можно импортировать в subprocess-процессе;
    - сохраняет снимок регистрации в SQLite;
    - удаляет записи для исчезнувших файлов.
    """
    ensure_directories(paths)

    effective_state_store = (
        state_store if state_store is not None else StateStore(paths.state_db)
    )
    venv_info = ensure_shared_venv(paths)

    existing_records = {
        item.relative_path: item
        for item in effective_state_store.list_registration_modules()
    }

    discovered_files = discover_python_files(paths.scripts)
    discovered_relative_paths = {
        str(file_path.resolve().relative_to(paths.scripts.resolve())).replace("\\", "/")
        for file_path in discovered_files
    }

    removed_files = 0
    for relative_path in set(existing_records) - discovered_relative_paths:
        if effective_state_store.delete_registration_module(relative_path):
            removed_files += 1

    processed_files = 0
    changed_files = 0
    unchanged_files = 0
    failed_files = 0
    installed_dependency_groups = 0

    force_reprocess = venv_info.created

    for file_path in discovered_files:
        processed_files += 1

        relative_path = str(
            file_path.resolve().relative_to(paths.scripts.resolve())
        ).replace("\\", "/")
        file_hash = compute_file_sha256(file_path)
        dependencies = extract_dependencies_from_module_docstring(file_path)
        previous_record = existing_records.get(relative_path)

        is_unchanged = (
            (not force_reprocess)
            and previous_record is not None
            and previous_record.file_hash_sha256 == file_hash
        )

        if is_unchanged:
            unchanged_files += 1
            continue

        try:
            if dependencies:
                install_requirements(paths, dependencies)
                installed_dependency_groups += 1

            inspect_script_file_in_subprocess(
                file_path,
                scripts_root=paths.scripts,
            )

            effective_state_store.upsert_registration_module(
                relative_path=relative_path,
                source_file=str(file_path.resolve()),
                file_hash_sha256=file_hash,
                dependencies=dependencies,
                status="registered",
                error_message=None,
            )
            changed_files += 1
        except Exception as error:  # noqa: BLE001
            effective_state_store.upsert_registration_module(
                relative_path=relative_path,
                source_file=str(file_path.resolve()),
                file_hash_sha256=file_hash,
                dependencies=dependencies,
                status="error",
                error_message=str(error),
            )
            failed_files += 1

    return RegistrationResult(
        processed_files=processed_files,
        changed_files=changed_files,
        unchanged_files=unchanged_files,
        removed_files=removed_files,
        failed_files=failed_files,
        installed_dependency_groups=installed_dependency_groups,
        venv_created=venv_info.created,
    )
