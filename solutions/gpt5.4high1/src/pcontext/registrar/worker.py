from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pcontext.registrar.introspection import inspect_script_file


def build_parser() -> argparse.ArgumentParser:
    """
    Создаёт CLI-парсер worker-процесса.

    Worker специально сделан отдельным модулем, чтобы основной процесс
    регистрации мог безопасно импортировать пользовательские скрипты
    в изолированной дочерней Python-процессе.
    """
    parser = argparse.ArgumentParser(prog="python -m pcontext.registrar.worker")
    parser.add_argument(
        "--scripts-root",
        required=True,
        help="Корневая папка пользовательских скриптов.",
    )
    parser.add_argument(
        "file",
        help="Путь к анализируемому Python-файлу.",
    )
    return parser


def main() -> int:
    """
    Точка входа worker-процесса.
    """
    parser = build_parser()
    namespace = parser.parse_args()

    try:
        scripts_root = Path(namespace.scripts_root).expanduser().resolve()
        file_path = Path(namespace.file).expanduser().resolve()

        result = inspect_script_file(file_path, scripts_root=scripts_root)
        print(result.model_dump_json(indent=2))
        return 0
    except Exception as error:  # noqa: BLE001
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
