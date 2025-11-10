"""OS-aware path resolution for application directories and config files.

This module ensures that Contextipy respects platform-specific conventions
for storing application data, configurations, and logs:
- Windows: uses APPDATA and LOCALAPPDATA environment variables
- macOS: uses ~/Library/Application Support and ~/Library/Logs
- Linux: follows XDG Base Directory specification
"""

from __future__ import annotations

import os
import platform
from pathlib import Path

APP_DIR_NAME = "contextipy"
SETTINGS_FILENAME = "settings.json"
PARAMETERS_FILENAME = "parameters.json"
MENU_VISIBILITY_FILENAME = "menu_visibility.json"
DATABASE_FILENAME = "registry.db"


def get_config_root() -> Path:
    """Return the platform-specific configuration root directory.

    - Windows: %APPDATA%\\contextipy
    - macOS: ~/Library/Application Support/contextipy
    - Linux: ~/.config/contextipy (or $XDG_CONFIG_HOME/contextipy)
    """
    system = platform.system()

    if system == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            base = Path(appdata)
        else:
            base = Path.home() / "AppData" / "Roaming"
        return ensure_directory(base / APP_DIR_NAME)

    if system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
        return ensure_directory(base / APP_DIR_NAME)

    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        base = Path(xdg_config)
    else:
        base = Path.home() / ".config"
    return ensure_directory(base / APP_DIR_NAME)


def get_data_root() -> Path:
    """Return the platform-specific data storage root directory.

    - Windows: %LOCALAPPDATA%\\contextipy
    - macOS: ~/Library/Application Support/contextipy
    - Linux: ~/.local/share/contextipy (or $XDG_DATA_HOME/contextipy)
    """
    system = platform.system()

    if system == "Windows":
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            base = Path(localappdata)
        else:
            appdata = os.environ.get("APPDATA")
            if appdata:
                base = Path(appdata)
            else:
                base = Path.home() / "AppData" / "Local"
        return ensure_directory(base / APP_DIR_NAME)

    if system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
        return ensure_directory(base / APP_DIR_NAME)

    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        base = Path(xdg_data)
    else:
        base = Path.home() / ".local" / "share"
    return ensure_directory(base / APP_DIR_NAME)


def get_logs_dir() -> Path:
    """Return the platform-specific logs directory.

    - Windows: %LOCALAPPDATA%\\contextipy\\logs
    - macOS: ~/Library/Logs/contextipy
    - Linux: ~/.local/share/contextipy/logs (or $XDG_DATA_HOME/contextipy/logs)
    """
    system = platform.system()

    if system == "Darwin":
        base = Path.home() / "Library" / "Logs"
        return ensure_directory(base / APP_DIR_NAME)

    return ensure_directory(get_data_root() / "logs")


def ensure_directory(path: Path) -> Path:
    """Ensure that a directory exists, creating it if necessary.

    Args:
        path: The directory path to ensure exists.

    Returns:
        The same path after ensuring its existence.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_settings_path() -> Path:
    """Return the path to the application settings file."""
    return get_config_root() / SETTINGS_FILENAME


def get_parameters_path() -> Path:
    """Return the path to the script parameters JSON file."""
    return get_data_root() / PARAMETERS_FILENAME


def get_menu_visibility_path() -> Path:
    """Return the path to the menu visibility flags JSON file."""
    return get_data_root() / MENU_VISIBILITY_FILENAME


def get_registry_path() -> Path:
    """Return the path to the script registry SQLite database."""
    return get_data_root() / DATABASE_FILENAME


__all__ = [
    "APP_DIR_NAME",
    "SETTINGS_FILENAME",
    "PARAMETERS_FILENAME",
    "MENU_VISIBILITY_FILENAME",
    "DATABASE_FILENAME",
    "get_config_root",
    "get_data_root",
    "get_logs_dir",
    "ensure_directory",
    "get_settings_path",
    "get_parameters_path",
    "get_menu_visibility_path",
    "get_registry_path",
]
