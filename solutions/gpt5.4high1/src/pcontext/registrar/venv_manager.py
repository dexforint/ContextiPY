from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass

from pcontext.config import PContextPaths, ensure_directories
from pcontext.runtime.python_env import get_shared_venv_python


# Это минимальный набор зависимостей, без которых worker-процессы
# не смогут импортировать сам пакет pcontext в общем venv.
_SHARED_VENV_BOOTSTRAP_REQUIREMENTS = [
    "pydantic>=2.8.2",
    "typing-extensions>=4.12.2",
]


@dataclass(frozen=True, slots=True)
class SharedVenvInfo:
    """
    Состояние общего виртуального окружения PContext.
    """

    python_executable: str
    created: bool


def _find_uv_executable() -> str:
    """
    Ищет исполняемый файл `uv` в PATH.
    """
    uv_path = shutil.which("uv")
    if uv_path is None:
        raise RuntimeError(
            "Executable 'uv' was not found. Install uv and make sure it is available in PATH."
        )

    return uv_path


def _run_uv_pip_install(python_executable: str, requirements: list[str]) -> None:
    """
    Выполняет `uv pip install` в указанный интерпретатор.
    """
    normalized_requirements = [item.strip() for item in requirements if item.strip()]
    if not normalized_requirements:
        return

    uv_executable = _find_uv_executable()

    command = [
        uv_executable,
        "pip",
        "install",
        "--python",
        python_executable,
        *normalized_requirements,
    ]

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr_text = completed.stderr.strip() or "Unknown uv pip install error."
        raise RuntimeError(
            "Failed to install requirements into the shared PContext venv: "
            f"{stderr_text}"
        )


def ensure_shared_venv(paths: PContextPaths) -> SharedVenvInfo:
    """
    Создаёт общее виртуальное окружение PContext, если его ещё нет,
    и гарантирует наличие bootstrap-зависимостей для worker-процессов.
    """
    ensure_directories(paths)

    python_path = get_shared_venv_python(paths.home)
    was_created = not python_path.is_file()

    if was_created:
        uv_executable = _find_uv_executable()
        command = [
            uv_executable,
            "venv",
            str(paths.venv),
            "--python",
            sys.executable,
        ]

        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            stderr_text = completed.stderr.strip() or "Unknown uv venv error."
            raise RuntimeError(
                f"Failed to create the shared PContext venv: {stderr_text}"
            )

    # ВАЖНО:
    # bootstrap-зависимости ставим всегда, а не только при первом создании venv.
    # Это позволяет исправить уже существующее окружение после обновления приложения.
    _run_uv_pip_install(
        str(python_path),
        _SHARED_VENV_BOOTSTRAP_REQUIREMENTS,
    )

    return SharedVenvInfo(
        python_executable=str(python_path),
        created=was_created,
    )


def install_requirements(paths: PContextPaths, requirements: list[str]) -> None:
    """
    Устанавливает список зависимостей в общее виртуальное окружение PContext.
    """
    venv_info = ensure_shared_venv(paths)
    _run_uv_pip_install(
        venv_info.python_executable,
        requirements,
    )
