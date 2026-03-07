from __future__ import annotations

from pathlib import Path

from pcontext.runtime.ipc_models import AgentEndpoint


def write_agent_endpoint(file_path: Path, endpoint: AgentEndpoint) -> None:
    """
    Атомарно сохраняет данные подключения к агенту.

    Это важный файл: его будут читать Rust bridge, Nautilus extension
    и отладочные CLI-команды.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = file_path.with_suffix(f"{file_path.suffix}.tmp")
    temporary_path.write_text(
        endpoint.model_dump_json(indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(file_path)


def read_agent_endpoint(file_path: Path) -> AgentEndpoint:
    """
    Загружает файл discovery и валидирует его.
    """
    payload = file_path.read_text(encoding="utf-8")
    return AgentEndpoint.model_validate_json(payload)


def remove_agent_endpoint(file_path: Path) -> None:
    """
    Тихо удаляет discovery-файл, если он существует.
    """
    try:
        file_path.unlink()
    except FileNotFoundError:
        pass
