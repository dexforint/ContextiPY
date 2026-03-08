from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pcontext.config import PContextPaths
from pcontext.runtime.discovery import read_agent_endpoint
from pcontext.runtime.ipc_client import send_request
from pcontext.runtime.ipc_models import ErrorResponse, PingRequest


@dataclass(frozen=True, slots=True)
class WindowsShellDiagnostics:
    """
    Сводка по состоянию безопасной Windows shell-интеграции.
    """

    runtime_dir: str
    config_path: str
    config_exists: bool
    config_error: str | None
    gui_executable: str | None
    launcher_exe: str | None
    auto_start_gui_if_missing: bool | None
    launcher_log_path: str
    launcher_log_exists: bool
    launcher_log_tail: str
    endpoint_path: str
    endpoint_exists: bool
    agent_available: bool


def collect_windows_shell_diagnostics(
    paths: PContextPaths,
    *,
    max_log_lines: int = 80,
) -> WindowsShellDiagnostics:
    """
    Собирает диагностическую информацию по Windows shell dev-layer.
    """
    runtime_dir = paths.runtime
    config_path = runtime_dir / "windows-shell-dev-config.json"
    launcher_log_path = runtime_dir / "windows-launcher.log"
    endpoint_path = paths.agent_endpoint

    gui_executable: str | None = None
    launcher_exe: str | None = None
    auto_start_gui_if_missing: bool | None = None
    config_error: str | None = None

    if config_path.is_file():
        try:
            config_payload = json.loads(config_path.read_text(encoding="utf-8-sig"))
            gui_executable = _optional_str(config_payload.get("gui_executable"))
            launcher_exe = _optional_str(config_payload.get("launcher_exe"))
            auto_start_gui_if_missing = _optional_bool(
                config_payload.get("auto_start_gui_if_missing")
            )
        except Exception as error:  # noqa: BLE001
            config_error = str(error)

    launcher_log_tail = ""
    if launcher_log_path.is_file():
        try:
            launcher_log_tail = _read_last_lines(
                launcher_log_path,
                max_lines=max_log_lines,
            )
        except Exception as error:  # noqa: BLE001
            launcher_log_tail = f"Не удалось прочитать launcher log: {error}"

    agent_available = False
    if endpoint_path.is_file():
        try:
            endpoint = read_agent_endpoint(endpoint_path)
            response = send_request(
                endpoint,
                PingRequest(token=endpoint.token),
                timeout_seconds=1.0,
            )
            agent_available = not isinstance(response, ErrorResponse)
        except Exception:
            agent_available = False

    return WindowsShellDiagnostics(
        runtime_dir=str(runtime_dir),
        config_path=str(config_path),
        config_exists=config_path.is_file(),
        config_error=config_error,
        gui_executable=gui_executable,
        launcher_exe=launcher_exe,
        auto_start_gui_if_missing=auto_start_gui_if_missing,
        launcher_log_path=str(launcher_log_path),
        launcher_log_exists=launcher_log_path.is_file(),
        launcher_log_tail=launcher_log_tail,
        endpoint_path=str(endpoint_path),
        endpoint_exists=endpoint_path.is_file(),
        agent_available=agent_available,
    )


def _read_last_lines(file_path: Path, *, max_lines: int) -> str:
    """
    Читает последние строки текстового файла.
    """
    text = file_path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    return "\n".join(lines[-max_lines:])


def _optional_str(value: object) -> str | None:
    """
    Возвращает строку или None.
    """
    return value if isinstance(value, str) else None


def _optional_bool(value: object) -> bool | None:
    """
    Возвращает bool или None.
    """
    return value if isinstance(value, bool) else None
