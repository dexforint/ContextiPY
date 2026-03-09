from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import winreg
except ImportError:  # pragma: no cover
    winreg = None  # type: ignore[assignment]


RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "PContext"


@dataclass(frozen=True, slots=True)
class WindowsAutostartInfo:
    """
    Сводка по Windows-автозапуску приложения.
    """

    supported: bool
    enabled: bool
    current_command: str | None
    expected_command: str | None


def is_windows_autostart_supported() -> bool:
    """
    Проверяет, доступен ли механизм Windows-autostart.
    """
    return os.name == "nt" and winreg is not None


def _resolve_no_console_python_executable() -> Path:
    """
    Возвращает Python-интерпретатор без консоли, если он доступен.
    """
    executable = Path(sys.executable).resolve()

    if executable.name.lower() == "pythonw.exe":
        return executable

    if executable.name.lower() == "python.exe":
        pythonw_path = executable.with_name("pythonw.exe")
        if pythonw_path.is_file():
            return pythonw_path

    return executable


def build_windows_gui_launch_command(*, hidden: bool = True) -> str:
    """
    Строит команду для запуска GUI PContext из Windows-autostart.

    Варианты:
    - при запуске из исходников: `pythonw.exe -m pcontext.cli gui --hidden`
    - при запуске из упакованного GUI exe: `pcontext-gui.exe --hidden`
    """
    executable = Path(sys.executable).resolve()
    hidden_args = ["--hidden"] if hidden else []

    if executable.name.lower() in {"python.exe", "pythonw.exe"}:
        launcher = _resolve_no_console_python_executable()
        command_parts = [str(launcher), "-m", "pcontext.cli", "gui", *hidden_args]
    else:
        command_parts = [str(executable), *hidden_args]

    return subprocess.list2cmdline(command_parts)


def get_windows_autostart_info() -> WindowsAutostartInfo:
    """
    Возвращает текущее состояние Windows-autostart.
    """
    if not is_windows_autostart_supported():
        return WindowsAutostartInfo(
            supported=False,
            enabled=False,
            current_command=None,
            expected_command=None,
        )

    current_command: str | None = None

    assert winreg is not None

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH) as key:
            value, _ = winreg.QueryValueEx(key, RUN_VALUE_NAME)
            if isinstance(value, str):
                current_command = value
    except FileNotFoundError:
        current_command = None

    return WindowsAutostartInfo(
        supported=True,
        enabled=current_command is not None,
        current_command=current_command,
        expected_command=build_windows_gui_launch_command(hidden=True),
    )


def set_windows_autostart_enabled(enabled: bool) -> None:
    """
    Включает или выключает Windows-autostart для PContext.
    """
    if not is_windows_autostart_supported():
        raise RuntimeError("Windows-autostart недоступен на этой платформе.")

    assert winreg is not None

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH) as key:
        if enabled:
            command = build_windows_gui_launch_command(hidden=True)
            winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, command)
            return

        try:
            winreg.DeleteValue(key, RUN_VALUE_NAME)
        except FileNotFoundError:
            pass
