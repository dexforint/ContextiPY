from __future__ import annotations

import os
import sys
from pathlib import Path


_SHARED_SITE_PACKAGES_ENV = "PCONTEXT_SHARED_SITE_PACKAGES"
_PROJECT_SRC_ENV = "PCONTEXT_PROJECT_SRC"


def get_runtime_project_src_path() -> Path:
    """
    Возвращает путь до директории `src`, доступной текущему процессу.

    В обычной разработке это исходная папка проекта.
    В frozen-сборке ожидается, что рядом с exe лежит папка `src`.
    """
    if getattr(sys, "frozen", False):
        frozen_src = Path(sys.executable).resolve().parent / "src"
        if frozen_src.is_dir():
            return frozen_src

    return Path(__file__).resolve().parents[2]


def get_shared_venv_dir(base_dir: Path) -> Path:
    return base_dir / "venv"


def get_shared_venv_python(base_dir: Path) -> Path:
    venv_dir = get_shared_venv_dir(base_dir)

    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"

    return venv_dir / "bin" / "python"


def get_shared_venv_site_packages(base_dir: Path) -> Path:
    venv_dir = get_shared_venv_dir(base_dir)

    if os.name == "nt":
        return venv_dir / "Lib" / "site-packages"

    version_tag = f"python{sys.version_info.major}.{sys.version_info.minor}"
    return venv_dir / "lib" / version_tag / "site-packages"


def build_subprocess_env(base_dir: Path) -> dict[str, str]:
    """
    Строит окружение для worker/service subprocess-процессов.
    """
    env = os.environ.copy()

    project_src = get_runtime_project_src_path()
    shared_site_packages = get_shared_venv_site_packages(base_dir)

    python_path_entries: list[str] = [str(project_src)]

    if shared_site_packages.is_dir():
        python_path_entries.append(str(shared_site_packages))

    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        python_path_entries.append(existing_pythonpath)

    env["PYTHONPATH"] = os.pathsep.join(python_path_entries)
    env[_PROJECT_SRC_ENV] = str(project_src)
    env[_SHARED_SITE_PACKAGES_ENV] = str(shared_site_packages)

    return env


def apply_internal_subprocess_paths_from_env() -> None:
    """
    Принудительно добавляет project src и shared site-packages в sys.path.
    """
    candidate_paths = [
        os.environ.get(_PROJECT_SRC_ENV),
        os.environ.get(_SHARED_SITE_PACKAGES_ENV),
    ]

    for raw_path in candidate_paths:
        if not raw_path:
            continue

        path = Path(raw_path)
        if not path.exists():
            continue

        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)
