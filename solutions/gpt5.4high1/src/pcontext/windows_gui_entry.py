from __future__ import annotations

import argparse
import sys

from pcontext.config import ensure_directories, get_paths
from pcontext.gui.app import run_gui
from pcontext.runtime.python_env import apply_internal_subprocess_paths_from_env


def build_parser() -> argparse.ArgumentParser:
    """
    Создаёт минимальный парсер для упакованного GUI exe.
    """
    parser = argparse.ArgumentParser(prog="pcontext-gui")
    parser.add_argument(
        "--hidden",
        action="store_true",
        help="Запустить GUI скрытым, только с tray icon.",
    )
    return parser


def _dispatch_internal_mode(argv: list[str]) -> int | None:
    """
    Перехватывает внутренние режимы frozen executable.
    """
    if not argv:
        return None

    mode = argv[0]

    # Для frozen subprocess-режимов вручную расширяем sys.path,
    # чтобы worker видел сам пакет pcontext и site-packages общего venv.
    apply_internal_subprocess_paths_from_env()

    if mode == "--pcontext-internal-registrar-worker":
        from pcontext.registrar.worker import main as worker_main

        sys.argv = [sys.argv[0], *argv[1:]]
        return worker_main()

    if mode == "--pcontext-internal-runner-worker":
        from pcontext.runner.worker import main as worker_main

        sys.argv = [sys.argv[0], *argv[1:]]
        return worker_main()

    if mode == "--pcontext-internal-service-worker":
        from pcontext.runner.service_worker import main as worker_main

        sys.argv = [sys.argv[0], *argv[1:]]
        return worker_main()

    return None


def main() -> int:
    """
    Точка входа Windows GUI exe.
    """
    internal_result = _dispatch_internal_mode(sys.argv[1:])
    if internal_result is not None:
        return internal_result

    parser = build_parser()
    namespace = parser.parse_args()

    paths = get_paths()
    ensure_directories(paths)
    return run_gui(paths, start_hidden=bool(namespace.hidden))


if __name__ == "__main__":
    raise SystemExit(main())
