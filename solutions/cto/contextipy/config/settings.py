"""Application settings management with dataclass and persistence support.

This module defines the Settings dataclass for application-level configuration
such as startup behavior and notification preferences, along with a store that
handles JSON serialization/deserialization and provides change notification hooks.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .paths import get_settings_path


@dataclass
class Settings:
    """Application-level settings.

    Attributes:
        launch_on_startup: Whether the application should start automatically at login.
        enable_notifications: Whether to show system notifications for events.
    """

    launch_on_startup: bool = False
    enable_notifications: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Settings:
        """Create Settings from a dictionary, ignoring unknown keys."""
        return cls(
            launch_on_startup=bool(data.get("launch_on_startup", False)),
            enable_notifications=bool(data.get("enable_notifications", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert Settings to a dictionary."""
        return asdict(self)


class SettingsStore:
    """Manages Settings persistence and change notifications.

    The store handles reading/writing settings to a JSON file and notifying
    registered listeners when settings are updated.
    """

    def __init__(self, path: Path | None = None) -> None:
        """Initialize the store with an optional custom path.

        Args:
            path: The path to the settings file. If None, uses the default
                  path from get_settings_path().
        """
        self._path = path or get_settings_path()
        self._listeners: list[Callable[[Settings], None]] = []

    def load(self) -> Settings:
        """Load settings from disk, or return defaults if the file doesn't exist."""
        if not self._path.exists():
            return Settings()

        try:
            with self._path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return Settings.from_dict(data)
        except (json.JSONDecodeError, OSError):
            return Settings()

    def save(self, settings: Settings) -> None:
        """Save settings to disk and notify all registered listeners.

        Args:
            settings: The Settings instance to persist.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with self._path.open("w", encoding="utf-8") as f:
                json.dump(settings.to_dict(), f, indent=2)
        except OSError:
            pass

        for listener in self._listeners:
            listener(settings)

    def on_change(self, listener: Callable[[Settings], None]) -> None:
        """Register a callback to be invoked whenever settings are saved.

        Args:
            listener: A callable that accepts a Settings instance.
        """
        self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[Settings], None]) -> None:
        """Unregister a previously registered listener.

        Args:
            listener: The callable to remove from the listener list.
        """
        if listener in self._listeners:
            self._listeners.remove(listener)


__all__ = ["Settings", "SettingsStore"]
