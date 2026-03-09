from __future__ import annotations

import sys

from pcontext.config import get_paths
from pcontext.runtime.python_env import get_shared_venv_python


def is_frozen_executable() -> bool:
    return bool(getattr(sys, "frozen", False))


def _build_frozen_external_worker_command(
    module_name: str, fallback_flag: str
) -> list[str]:
    """
    Для frozen exe стараемся запускать worker через shared venv python,
    а не через сам собранный GUI exe.

    Это даёт:
    - полный stdlib;
    - доступ ко всем установленным зависимостям;
    - меньше проблем с hidden imports PyInstaller.
    """
    shared_python = get_shared_venv_python(get_paths().home)
    if shared_python.is_file():
        return [str(shared_python), "-m", module_name]

    return [sys.executable, fallback_flag]


def build_registrar_worker_command() -> list[str]:
    if is_frozen_executable():
        return _build_frozen_external_worker_command(
            "pcontext.registrar.worker",
            "--pcontext-internal-registrar-worker",
        )

    return [sys.executable, "-m", "pcontext.registrar.worker"]


def build_runner_worker_command() -> list[str]:
    if is_frozen_executable():
        return _build_frozen_external_worker_command(
            "pcontext.runner.worker",
            "--pcontext-internal-runner-worker",
        )

    return [sys.executable, "-m", "pcontext.runner.worker"]


def build_service_worker_command() -> list[str]:
    if is_frozen_executable():
        return _build_frozen_external_worker_command(
            "pcontext.runner.service_worker",
            "--pcontext-internal-service-worker",
        )

    return [sys.executable, "-m", "pcontext.runner.service_worker"]
