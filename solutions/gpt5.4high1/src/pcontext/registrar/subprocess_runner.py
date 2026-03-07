from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from pcontext.registrar.introspection import discover_python_files
from pcontext.registrar.models import ModuleInspectionResult


def inspect_script_file_in_subprocess(
    file_path: Path,
    *,
    scripts_root: Path,
) -> ModuleInspectionResult:
    """
    Анализирует один скрипт в отдельном Python-процессе.

    Это важно, потому что пользовательский модуль может:
    - импортировать тяжёлые библиотеки;
    - менять глобальное состояние;
    - аварийно завершаться при импорте.
    """
    command = [
        sys.executable,
        "-m",
        "pcontext.registrar.worker",
        "--scripts-root",
        str(scripts_root),
        str(file_path),
    ]

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if completed.returncode != 0:
        stderr_text = completed.stderr.strip() or "Неизвестная ошибка worker-процесса."
        raise RuntimeError(
            f"Не удалось проанализировать файл '{file_path}': {stderr_text}"
        )

    return ModuleInspectionResult.model_validate_json(completed.stdout)


def scan_scripts_in_subprocess(
    scripts_root: Path,
) -> list[ModuleInspectionResult]:
    """
    Сканирует всю папку scripts и возвращает только файлы,
    в которых действительно найдены PContext-определения.
    """
    results: list[ModuleInspectionResult] = []

    for file_path in discover_python_files(scripts_root):
        result = inspect_script_file_in_subprocess(
            file_path,
            scripts_root=scripts_root,
        )
        if result.has_definitions:
            results.append(result)

    return results
