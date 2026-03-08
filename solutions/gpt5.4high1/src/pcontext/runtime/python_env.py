from __future__ import annotations

import os
import sys
from pathlib import Path


def get_project_src_path() -> Path:
    """
    Возвращает путь до директории `src` текущего проекта.

    Он нужен, чтобы subprocess-процессы могли импортировать сам пакет pcontext,
    даже если запускаются не из основного uv-окружения проекта.
    """
    return Path(__file__).resolve().parents[2]


def get_shared_venv_dir(base_dir: Path) -> Path:
    """
    Возвращает путь до общего виртуального окружения PContext.
    """
    return base_dir / "venv"


def get_shared_venv_python(base_dir: Path) -> Path:
    """
    Возвращает путь до интерпретатора Python внутри общего venv.
    """
    venv_dir = get_shared_venv_dir(base_dir)

    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"

    return venv_dir / "bin" / "python"


def get_shared_venv_site_packages(base_dir: Path) -> Path:
    """
    Возвращает путь до site-packages внутри общего venv.

    Мы предполагаем, что venv создаётся под той же версией Python,
    что и основное приложение PContext.
    """
    venv_dir = get_shared_venv_dir(base_dir)

    if os.name == "nt":
        return venv_dir / "Lib" / "site-packages"

    version_tag = f"python{sys.version_info.major}.{sys.version_info.minor}"
    return venv_dir / "lib" / version_tag / "site-packages"


def build_subprocess_env(base_dir: Path) -> dict[str, str]:
    """
    Строит окружение для worker/service subprocess-процессов.

    В `PYTHONPATH` добавляются:
    - `src` текущего проекта, чтобы subprocess видел пакет `pcontext`;
    - `site-packages` общего venv, чтобы subprocess видел зависимости скриптов.
    """
    env = os.environ.copy()

    python_path_entries: list[str] = [str(get_project_src_path())]

    shared_site_packages = get_shared_venv_site_packages(base_dir)
    if shared_site_packages.is_dir():
        python_path_entries.append(str(shared_site_packages))

    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        python_path_entries.append(existing_pythonpath)

    env["PYTHONPATH"] = os.pathsep.join(python_path_entries)
    return env
