from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass

from pcontext.config import PContextPaths, ensure_directories
from pcontext.runtime.python_env import get_shared_venv_python


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
            "Не найден исполняемый файл uv. Установи uv и убедись, что он доступен в PATH."
        )

    return uv_path


def ensure_shared_venv(paths: PContextPaths) -> SharedVenvInfo:
    """
    Создаёт общее виртуальное окружение PContext, если его ещё нет.
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
            stderr_text = completed.stderr.strip() or "Неизвестная ошибка uv venv."
            raise RuntimeError(f"Не удалось создать общее venv PContext: {stderr_text}")

    return SharedVenvInfo(
        python_executable=str(python_path),
        created=was_created,
    )


def install_requirements(paths: PContextPaths, requirements: list[str]) -> None:
    """
    Устанавливает список зависимостей в общее виртуальное окружение PContext.
    """
    normalized_requirements = [item.strip() for item in requirements if item.strip()]
    if not normalized_requirements:
        return

    venv_info = ensure_shared_venv(paths)
    uv_executable = _find_uv_executable()

    command = [
        uv_executable,
        "pip",
        "install",
        "--python",
        venv_info.python_executable,
        *normalized_requirements,
    ]

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr_text = completed.stderr.strip() or "Неизвестная ошибка uv pip install."
        raise RuntimeError(
            "Не удалось установить зависимости в общее venv PContext: " f"{stderr_text}"
        )
