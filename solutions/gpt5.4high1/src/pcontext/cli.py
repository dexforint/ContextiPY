from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pcontext.agent.catalog import load_agent_catalog
from pcontext.agent.server import serve_agent
from pcontext.config import ensure_directories, get_paths
from pcontext.gui.app import run_gui
from pcontext.registrar.subprocess_runner import (
    inspect_script_file_in_subprocess,
    scan_scripts_in_subprocess,
)
from pcontext.runtime.action_codec import SERIALIZED_ACTION_ADAPTER
from pcontext.runtime.action_executor import execute_serialized_action
from pcontext.runtime.discovery import read_agent_endpoint
from pcontext.runtime.ipc_client import send_request
from pcontext.runtime.ipc_models import (
    ErrorResponse,
    InvokeMenuItemRequest,
    ListServicesRequest,
    PingRequest,
    QueryMenuRequest,
    ReloadRegistryRequest,
    ShellContext,
    ShellEntry,
    StartServiceRequest,
    StopServiceRequest,
)
from pcontext.storage.state import StateStore
from pcontext.storage.views import build_parameter_views


def _print_json(payload: object) -> None:
    """
    Единая печать JSON в CLI.
    """
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _resolve_scripts_root(raw_value: str | None) -> Path:
    """
    Возвращает корневую папку пользовательских скриптов.
    """
    if raw_value is not None:
        return Path(raw_value).expanduser().resolve()

    return get_paths().scripts.resolve()


def _load_state_store() -> StateStore:
    """
    Создаёт доступ к SQLite-хранилищу состояния.
    """
    return StateStore(get_paths().state_db)


def _parse_json_value(raw_value: str) -> Any:
    """
    Парсит значение из CLI.

    Если строка не является корректным JSON, она считается обычным текстом.
    """
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        return raw_value


def _add_context_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Добавляет аргументы, которые описывают shell-контекст.
    """
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--background",
        help="Путь к папке, в которой пользователь открыл контекстное меню на пустой области.",
    )
    group.add_argument(
        "--select",
        nargs="+",
        help="Один или несколько выбранных файлов или папок.",
    )


def _build_context_from_args(namespace: argparse.Namespace) -> ShellContext:
    """
    Собирает shell-контекст из CLI-аргументов.
    """
    background = getattr(namespace, "background", None)
    selection = getattr(namespace, "select", None)

    if isinstance(background, str):
        folder_path = Path(background).expanduser()
        if not folder_path.exists():
            raise FileNotFoundError(f"Папка не найдена: {folder_path}")
        if not folder_path.is_dir():
            raise NotADirectoryError(f"Ожидалась папка: {folder_path}")

        return ShellContext(
            source="background",
            current_folder=str(folder_path.resolve()),
            entries=[],
        )

    if isinstance(selection, list):
        if not selection:
            raise ValueError("Нужно передать хотя бы один путь в --select.")

        entries: list[ShellEntry] = []
        current_folder: Path | None = None

        for raw_path in selection:
            path = Path(raw_path).expanduser()
            if not path.exists():
                raise FileNotFoundError(f"Путь не найден: {path}")

            resolved_path = path.resolve()
            entry_type = "folder" if resolved_path.is_dir() else "file"
            entries.append(
                ShellEntry(
                    path=str(resolved_path),
                    entry_type=entry_type,
                )
            )

            if current_folder is None:
                current_folder = resolved_path.parent

        return ShellContext(
            source="selection",
            current_folder=str(current_folder) if current_folder is not None else None,
            entries=entries,
        )

    raise RuntimeError("Не удалось собрать shell-контекст из аргументов.")


def build_parser() -> argparse.ArgumentParser:
    """
    Создаёт CLI-парсер проекта.
    """
    parser = argparse.ArgumentParser(prog="pcontext")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("paths", help="Показать стандартные директории PContext.")
    subparsers.add_parser("init-dirs", help="Создать стандартные директории PContext.")
    subparsers.add_parser("agent", help="Запустить IPC-агент в foreground-режиме.")
    subparsers.add_parser("gui", help="Запустить tray и GUI приложения.")
    subparsers.add_parser("agent-ping", help="Проверить, что агент отвечает.")
    subparsers.add_parser(
        "reload-registry",
        help="Попросить агент пересканировать папку пользовательских скриптов.",
    )
    subparsers.add_parser(
        "list-services", help="Показать состояние всех зарегистрированных сервисов."
    )

    start_service_parser = subparsers.add_parser(
        "start-service", help="Запустить сервис."
    )
    start_service_parser.add_argument("service_id", help="Идентификатор сервиса.")

    stop_service_parser = subparsers.add_parser(
        "stop-service", help="Остановить сервис."
    )
    stop_service_parser.add_argument("service_id", help="Идентификатор сервиса.")

    query_parser = subparsers.add_parser(
        "query-menu",
        help="Запросить у агента список видимых пунктов меню.",
    )
    _add_context_arguments(query_parser)

    invoke_parser = subparsers.add_parser(
        "invoke-menu-item",
        help="Попросить агента выполнить пункт меню.",
    )
    invoke_parser.add_argument("menu_item_id", help="Идентификатор пункта меню.")
    _add_context_arguments(invoke_parser)

    inspect_parser = subparsers.add_parser(
        "inspect-script",
        help="Проанализировать один пользовательский Python-скрипт.",
    )
    inspect_parser.add_argument("file", help="Путь к .py файлу.")
    inspect_parser.add_argument(
        "--scripts-root",
        default=None,
        help="Корень папки scripts. По умолчанию используется ~/.pcontext/scripts",
    )

    scan_parser = subparsers.add_parser(
        "scan-scripts",
        help="Просканировать всю папку пользовательских скриптов.",
    )
    scan_parser.add_argument(
        "--scripts-root",
        default=None,
        help="Корень папки scripts. По умолчанию используется ~/.pcontext/scripts",
    )

    show_params_parser = subparsers.add_parser(
        "show-params",
        help="Показать все обнаруженные параметры и их текущие значения.",
    )
    show_params_parser.add_argument(
        "--scripts-root",
        default=None,
        help="Корень папки scripts. По умолчанию используется ~/.pcontext/scripts",
    )

    set_param_parser = subparsers.add_parser(
        "set-param",
        help="Сохранить значение параметра.",
    )
    set_param_parser.add_argument(
        "owner_id", help="Идентификатор скрипта, сервиса или service.script."
    )
    set_param_parser.add_argument("param_name", help="Имя параметра.")
    set_param_parser.add_argument("value_json", help="Значение параметра.")

    reset_param_parser = subparsers.add_parser(
        "reset-param",
        help="Сбросить одно сохранённое значение параметра.",
    )
    reset_param_parser.add_argument(
        "owner_id", help="Идентификатор владельца параметра."
    )
    reset_param_parser.add_argument("param_name", help="Имя параметра.")

    reset_owner_parser = subparsers.add_parser(
        "reset-owner-params",
        help="Сбросить все сохранённые параметры конкретного скрипта или сервиса.",
    )
    reset_owner_parser.add_argument(
        "owner_id", help="Идентификатор владельца параметров."
    )

    show_logs_parser = subparsers.add_parser(
        "show-logs",
        help="Показать последние записи логов.",
    )
    show_logs_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Сколько последних записей показать.",
    )

    replay_log_parser = subparsers.add_parser(
        "replay-log-action",
        help="Повторить сохранённое действие из записи лога.",
    )
    replay_log_parser.add_argument(
        "log_id", type=int, help="Идентификатор записи лога."
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """
    Точка входа CLI.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    parser = build_parser()
    namespace = parser.parse_args(argv)

    try:
        if namespace.command == "paths":
            paths = get_paths()
            _print_json(paths.as_dict())
            return 0

        if namespace.command == "init-dirs":
            paths = get_paths()
            ensure_directories(paths)
            _print_json(paths.as_dict())
            return 0

        if namespace.command == "agent":
            paths = get_paths()
            ensure_directories(paths)
            serve_agent(paths)
            return 0

        if namespace.command == "gui":
            paths = get_paths()
            ensure_directories(paths)
            return run_gui(paths)

        if namespace.command == "agent-ping":
            paths = get_paths()
            endpoint = read_agent_endpoint(paths.agent_endpoint)
            response = send_request(endpoint, PingRequest(token=endpoint.token))
            _print_json(response.model_dump(mode="json"))
            return 0

        if namespace.command == "reload-registry":
            paths = get_paths()
            endpoint = read_agent_endpoint(paths.agent_endpoint)
            response = send_request(
                endpoint,
                ReloadRegistryRequest(token=endpoint.token),
            )
            if isinstance(response, ErrorResponse):
                _print_json(response.model_dump(mode="json"))
                return 1
            _print_json(response.model_dump(mode="json"))
            return 0

        if namespace.command == "list-services":
            paths = get_paths()
            endpoint = read_agent_endpoint(paths.agent_endpoint)
            response = send_request(
                endpoint,
                ListServicesRequest(token=endpoint.token),
            )
            if isinstance(response, ErrorResponse):
                _print_json(response.model_dump(mode="json"))
                return 1
            _print_json(response.model_dump(mode="json"))
            return 0

        if namespace.command == "start-service":
            paths = get_paths()
            endpoint = read_agent_endpoint(paths.agent_endpoint)
            response = send_request(
                endpoint,
                StartServiceRequest(
                    token=endpoint.token,
                    service_id=namespace.service_id,
                ),
            )
            if isinstance(response, ErrorResponse):
                _print_json(response.model_dump(mode="json"))
                return 1
            _print_json(response.model_dump(mode="json"))
            return 0

        if namespace.command == "stop-service":
            paths = get_paths()
            endpoint = read_agent_endpoint(paths.agent_endpoint)
            response = send_request(
                endpoint,
                StopServiceRequest(
                    token=endpoint.token,
                    service_id=namespace.service_id,
                ),
            )
            if isinstance(response, ErrorResponse):
                _print_json(response.model_dump(mode="json"))
                return 1
            _print_json(response.model_dump(mode="json"))
            return 0

        if namespace.command == "query-menu":
            paths = get_paths()
            endpoint = read_agent_endpoint(paths.agent_endpoint)
            context = _build_context_from_args(namespace)
            response = send_request(
                endpoint,
                QueryMenuRequest(
                    token=endpoint.token,
                    context=context,
                ),
            )
            if isinstance(response, ErrorResponse):
                _print_json(response.model_dump(mode="json"))
                return 1
            _print_json(response.model_dump(mode="json"))
            return 0

        if namespace.command == "invoke-menu-item":
            paths = get_paths()
            endpoint = read_agent_endpoint(paths.agent_endpoint)
            context = _build_context_from_args(namespace)
            response = send_request(
                endpoint,
                InvokeMenuItemRequest(
                    token=endpoint.token,
                    menu_item_id=namespace.menu_item_id,
                    context=context,
                ),
            )
            if isinstance(response, ErrorResponse):
                _print_json(response.model_dump(mode="json"))
                return 1
            _print_json(response.model_dump(mode="json"))
            return 0

        if namespace.command == "inspect-script":
            scripts_root = _resolve_scripts_root(namespace.scripts_root)
            file_path = Path(namespace.file).expanduser().resolve()
            result = inspect_script_file_in_subprocess(
                file_path,
                scripts_root=scripts_root,
            )
            _print_json(result.model_dump(mode="json"))
            return 0

        if namespace.command == "scan-scripts":
            scripts_root = _resolve_scripts_root(namespace.scripts_root)
            results = scan_scripts_in_subprocess(scripts_root)
            _print_json([result.model_dump(mode="json") for result in results])
            return 0

        if namespace.command == "show-params":
            scripts_root = _resolve_scripts_root(namespace.scripts_root)
            state_store = _load_state_store()
            catalog = load_agent_catalog(scripts_root)
            views = build_parameter_views(catalog, state_store)
            _print_json(
                [
                    {
                        "owner_kind": item.owner_kind,
                        "owner_id": item.owner_id,
                        "owner_title": item.owner_title,
                        "param_name": item.param_name,
                        "default_value": item.default_value,
                        "current_value": item.current_value,
                        "has_override": item.has_override,
                    }
                    for item in views
                ]
            )
            return 0

        if namespace.command == "set-param":
            state_store = _load_state_store()
            value = _parse_json_value(namespace.value_json)
            state_store.set_parameter_value(
                namespace.owner_id,
                namespace.param_name,
                value,
            )
            _print_json(
                {
                    "owner_id": namespace.owner_id,
                    "param_name": namespace.param_name,
                    "saved_value": value,
                }
            )
            return 0

        if namespace.command == "reset-param":
            state_store = _load_state_store()
            removed = state_store.reset_parameter_value(
                namespace.owner_id,
                namespace.param_name,
            )
            _print_json(
                {
                    "owner_id": namespace.owner_id,
                    "param_name": namespace.param_name,
                    "removed": removed,
                }
            )
            return 0

        if namespace.command == "reset-owner-params":
            state_store = _load_state_store()
            removed_count = state_store.reset_all_parameter_values(namespace.owner_id)
            _print_json(
                {
                    "owner_id": namespace.owner_id,
                    "removed_count": removed_count,
                }
            )
            return 0

        if namespace.command == "show-logs":
            state_store = _load_state_store()
            logs = state_store.list_run_logs(limit=namespace.limit)
            _print_json(
                [
                    {
                        "log_id": item.log_id,
                        "created_at_utc": item.created_at_utc,
                        "invocation_kind": item.invocation_kind,
                        "command_id": item.command_id,
                        "title": item.title,
                        "duration_ms": item.duration_ms,
                        "success": item.success,
                        "message": item.message,
                        "has_action": item.action_json is not None,
                    }
                    for item in logs
                ]
            )
            return 0

        if namespace.command == "replay-log-action":
            state_store = _load_state_store()
            log_record = state_store.get_run_log(namespace.log_id)
            if log_record is None:
                raise RuntimeError(f"Запись лога с id={namespace.log_id} не найдена.")

            if log_record.action_json is None:
                raise RuntimeError("У этой записи лога нет сохранённого действия.")

            action = SERIALIZED_ACTION_ADAPTER.validate_json(log_record.action_json)
            result_message = execute_serialized_action(action)

            _print_json(
                {
                    "log_id": log_record.log_id,
                    "title": log_record.title,
                    "result": result_message,
                }
            )
            return 0

        parser.print_help()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as error:  # noqa: BLE001
        print(str(error), file=sys.stderr)
        return 1
