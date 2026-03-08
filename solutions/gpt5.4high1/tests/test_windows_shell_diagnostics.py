from __future__ import annotations

from pathlib import Path

from pcontext.config import get_paths
from pcontext.gui.windows_shell_diagnostics import collect_windows_shell_diagnostics
from pcontext.runtime.ipc_models import AgentEndpoint, PingResponse


def test_collect_windows_shell_diagnostics_reads_config_and_log(
    monkeypatch, tmp_path: Path
) -> None:
    """
    Диагностика Windows shell должна уметь читать config, launcher log и endpoint.
    """
    paths = get_paths(tmp_path / ".pcontext")
    paths.runtime.mkdir(parents=True, exist_ok=True)

    config_path = paths.runtime / "windows-shell-dev-config.json"
    config_path.write_text(
        """
{
  "gui_executable": "pythonw.exe",
  "gui_args": ["-m", "pcontext.cli", "gui"],
  "working_directory": "C:/project",
  "auto_start_gui_if_missing": true,
  "launcher_exe": "C:/launcher.exe",
  "icon_path": "C:/icon.ico"
}
""".lstrip(),
        encoding="utf-8",
    )

    log_path = paths.runtime / "windows-launcher.log"
    log_path.write_text(
        "line1\nline2\nline3\n",
        encoding="utf-8",
    )

    endpoint_path = paths.agent_endpoint
    endpoint_path.write_text(
        """
{
  "protocol_version": 1,
  "host": "127.0.0.1",
  "port": 12345,
  "token": "token",
  "pid": 100
}
""".lstrip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "pcontext.gui.windows_shell_diagnostics.read_agent_endpoint",
        lambda _path: AgentEndpoint(
            host="127.0.0.1",
            port=12345,
            token="token",
            pid=100,
        ),
    )
    monkeypatch.setattr(
        "pcontext.gui.windows_shell_diagnostics.send_request",
        lambda endpoint, request, timeout_seconds=1.0: PingResponse(pid=endpoint.pid),
    )

    diagnostics = collect_windows_shell_diagnostics(paths, max_log_lines=2)

    assert diagnostics.config_exists is True
    assert diagnostics.gui_executable == "pythonw.exe"
    assert diagnostics.launcher_exe == "C:/launcher.exe"
    assert diagnostics.auto_start_gui_if_missing is True
    assert diagnostics.launcher_log_exists is True
    assert diagnostics.launcher_log_tail == "line2\nline3"
    assert diagnostics.endpoint_exists is True
    assert diagnostics.agent_available is True
