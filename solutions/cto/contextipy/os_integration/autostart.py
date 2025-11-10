"""Platform-specific auto-start integration for ContextiPY.

This module provides helpers to enable or disable application auto-start at
user login. The implementation targets per-user registration without elevation:

- Windows: Uses the Run key in HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
- Linux: Creates a .desktop file in ~/.config/autostart
"""

from __future__ import annotations

import logging
import os
import platform
import sys
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AutostartResult:
    """Outcome of an auto-start operation."""

    success: bool
    message: str | None = None
    error: str | None = None


def is_windows() -> bool:
    """Return ``True`` when running on a Windows platform."""
    return sys.platform == "win32" or platform.system() == "Windows"


def is_linux() -> bool:
    """Return ``True`` when running on a Linux platform."""
    return sys.platform.startswith("linux") or platform.system() == "Linux"


def get_executable_path() -> Path:
    """Return the path to the Python executable running ContextiPY."""
    return Path(sys.executable)


def get_autostart_directory_linux() -> Path:
    """Return the directory where autostart .desktop files should be placed."""
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        base = Path(xdg_config_home)
    else:
        base = Path.home() / ".config"
    return base / "autostart"


def enable_autostart(*, app_name: str = "ContextiPY", command_args: list[str] | None = None) -> AutostartResult:
    """Enable application auto-start at user login.

    Args:
        app_name: The application name for registration.
        command_args: Optional command-line arguments to pass to the executable.

    Returns:
        AutostartResult indicating success or failure.
    """
    if is_windows():
        return _enable_autostart_windows(app_name=app_name, command_args=command_args)
    elif is_linux():
        return _enable_autostart_linux(app_name=app_name, command_args=command_args)
    else:
        return AutostartResult(
            success=False,
            error="Auto-start is only supported on Windows and Linux platforms",
        )


def disable_autostart(*, app_name: str = "ContextiPY") -> AutostartResult:
    """Disable application auto-start at user login.

    Args:
        app_name: The application name for registration.

    Returns:
        AutostartResult indicating success or failure.
    """
    if is_windows():
        return _disable_autostart_windows(app_name=app_name)
    elif is_linux():
        return _disable_autostart_linux(app_name=app_name)
    else:
        return AutostartResult(
            success=False,
            error="Auto-start is only supported on Windows and Linux platforms",
        )


def is_autostart_enabled(*, app_name: str = "ContextiPY") -> bool:
    """Check whether application auto-start is currently enabled.

    Args:
        app_name: The application name for registration.

    Returns:
        True if auto-start is enabled, False otherwise.
    """
    if is_windows():
        return _is_autostart_enabled_windows(app_name=app_name)
    elif is_linux():
        return _is_autostart_enabled_linux(app_name=app_name)
    else:
        return False


def _enable_autostart_windows(*, app_name: str, command_args: list[str] | None = None) -> AutostartResult:
    """Enable auto-start on Windows via registry Run key."""
    if not is_windows():
        return AutostartResult(success=False, error="Windows registry is only available on Windows")

    try:
        import winreg  # type: ignore
    except ImportError:  # pragma: no cover
        return AutostartResult(success=False, error="winreg module is not available")

    executable = get_executable_path()
    command_parts = [f'"{executable}"', "-m", "contextipy"]
    if command_args:
        command_parts.extend(command_args)
    command_line = " ".join(command_parts)

    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, command_line)
        winreg.CloseKey(key)
        logger.info("Enabled auto-start for %s on Windows", app_name)
        return AutostartResult(success=True, message=f"Auto-start enabled for {app_name}")
    except OSError as exc:
        logger.error("Failed to enable auto-start on Windows: %s", exc)
        return AutostartResult(success=False, error=f"Registry operation failed: {exc}")


def _disable_autostart_windows(*, app_name: str) -> AutostartResult:
    """Disable auto-start on Windows via registry Run key."""
    if not is_windows():
        return AutostartResult(success=False, error="Windows registry is only available on Windows")

    try:
        import winreg  # type: ignore
    except ImportError:  # pragma: no cover
        return AutostartResult(success=False, error="winreg module is not available")

    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE)
        try:
            winreg.DeleteValue(key, app_name)
            logger.info("Disabled auto-start for %s on Windows", app_name)
            result = AutostartResult(success=True, message=f"Auto-start disabled for {app_name}")
        except FileNotFoundError:
            result = AutostartResult(success=True, message=f"Auto-start was not enabled for {app_name}")
        finally:
            winreg.CloseKey(key)
        return result
    except OSError as exc:
        logger.error("Failed to disable auto-start on Windows: %s", exc)
        return AutostartResult(success=False, error=f"Registry operation failed: {exc}")


def _is_autostart_enabled_windows(*, app_name: str) -> bool:
    """Check whether auto-start is enabled on Windows."""
    if not is_windows():
        return False

    try:
        import winreg  # type: ignore
    except ImportError:  # pragma: no cover
        return False

    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, app_name)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except OSError:
        return False


def _enable_autostart_linux(*, app_name: str, command_args: list[str] | None = None) -> AutostartResult:
    """Enable auto-start on Linux via .desktop file."""
    if not is_linux():
        return AutostartResult(success=False, error="Desktop files are only available on Linux")

    autostart_dir = get_autostart_directory_linux()
    desktop_file_path = autostart_dir / f"{app_name}.desktop"

    try:
        autostart_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.error("Failed to create autostart directory: %s", exc)
        return AutostartResult(success=False, error=f"Failed to create autostart directory: {exc}")

    executable = get_executable_path()
    command_parts = [str(executable), "-m", "contextipy"]
    if command_args:
        command_parts.extend(command_args)
    command_line = " ".join(command_parts)

    desktop_content = f"""[Desktop Entry]
Type=Application
Name={app_name}
Comment=ContextiPY - Context Menu Scripts Manager
Exec={command_line}
Terminal=false
StartupNotify=false
X-GNOME-Autostart-enabled=true
"""

    try:
        desktop_file_path.write_text(desktop_content, encoding="utf-8")
        logger.info("Enabled auto-start for %s on Linux", app_name)
        return AutostartResult(success=True, message=f"Auto-start enabled for {app_name}")
    except OSError as exc:
        logger.error("Failed to write autostart desktop file: %s", exc)
        return AutostartResult(success=False, error=f"Failed to write desktop file: {exc}")


def _disable_autostart_linux(*, app_name: str) -> AutostartResult:
    """Disable auto-start on Linux by removing .desktop file."""
    if not is_linux():
        return AutostartResult(success=False, error="Desktop files are only available on Linux")

    autostart_dir = get_autostart_directory_linux()
    desktop_file_path = autostart_dir / f"{app_name}.desktop"

    try:
        if desktop_file_path.exists():
            desktop_file_path.unlink()
            logger.info("Disabled auto-start for %s on Linux", app_name)
            return AutostartResult(success=True, message=f"Auto-start disabled for {app_name}")
        else:
            return AutostartResult(success=True, message=f"Auto-start was not enabled for {app_name}")
    except OSError as exc:
        logger.error("Failed to remove autostart desktop file: %s", exc)
        return AutostartResult(success=False, error=f"Failed to remove desktop file: {exc}")


def _is_autostart_enabled_linux(*, app_name: str) -> bool:
    """Check whether auto-start is enabled on Linux."""
    if not is_linux():
        return False

    autostart_dir = get_autostart_directory_linux()
    desktop_file_path = autostart_dir / f"{app_name}.desktop"
    return desktop_file_path.exists()


__all__ = [
    "AutostartResult",
    "enable_autostart",
    "disable_autostart",
    "is_autostart_enabled",
    "is_windows",
    "is_linux",
    "get_executable_path",
    "get_autostart_directory_linux",
]
