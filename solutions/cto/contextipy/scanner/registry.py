"""Registry for script metadata including persistence and notification hooks."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..config.persistence import ScriptRegistry
from .dependency_installer import (
    DependencyInstaller,
    InstallResult,
    parse_requirements_from_docstring,
)
from .script_scanner import ScannedScript, ScanResult, ScriptScanner

logger = logging.getLogger(__name__)


@dataclass
class ScriptSettings:
    """User-configurable settings for a registered script."""

    enabled: bool = True
    startup: bool = False
    parameter_overrides: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "startup": self.startup,
            "parameter_overrides": self.parameter_overrides or {},
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ScriptSettings:
        overrides = data.get("parameter_overrides")
        if not isinstance(overrides, dict):
            overrides = None
        return ScriptSettings(
            enabled=bool(data.get("enabled", True)),
            startup=bool(data.get("startup", False)),
            parameter_overrides=overrides,
        )


@dataclass
class RegisteredScript:
    """Complete script metadata including scanned info and user settings."""

    scanned: ScannedScript
    settings: ScriptSettings

    @property
    def script_id(self) -> str:
        return self.scanned.script_id

    @property
    def enabled(self) -> bool:
        return self.settings.enabled

    @property
    def startup(self) -> bool:
        return self.settings.startup

    def to_dict(self) -> dict[str, Any]:
        script_dict = asdict(self.scanned)
        script_dict["file_path"] = str(self.scanned.file_path)
        script_dict["group"] = list(self.scanned.group)
        script_dict["accepts"] = list(self.scanned.accepts)
        script_dict["categories"] = list(self.scanned.categories)
        script_dict["parameters"] = list(self.scanned.parameters)
        return {
            "scanned": script_dict,
            "settings": self.settings.to_dict(),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> RegisteredScript:
        scanned_data_raw = dict(data["scanned"])
        scanned_data_raw["file_path"] = Path(scanned_data_raw["file_path"])
        scanned_data_raw["group"] = tuple(scanned_data_raw.get("group", ()))
        scanned_data_raw["accepts"] = tuple(scanned_data_raw.get("accepts", ()))
        scanned_data_raw["categories"] = tuple(scanned_data_raw.get("categories", ()))
        scanned_data_raw["parameters"] = tuple(scanned_data_raw.get("parameters", ()))
        scanned = ScannedScript(**scanned_data_raw)
        settings = ScriptSettings.from_dict(dict(data.get("settings", {})))
        return RegisteredScript(scanned=scanned, settings=settings)


ChangeCallback = Callable[[], None]


class ScriptMetadataRegistry:
    """Registry managing script metadata with persistence and change notifications."""

    def __init__(
        self,
        storage: ScriptRegistry | None = None,
        scanner: ScriptScanner | None = None,
        dependency_installer: DependencyInstaller | None = None,
    ) -> None:
        self._storage = storage or ScriptRegistry()
        self._scanner = scanner
        self._dependency_installer = dependency_installer
        self._scripts: dict[str, RegisteredScript] = {}
        self._callbacks: list[ChangeCallback] = []

    def load(self) -> None:
        """Load persisted script metadata from storage."""

        stored_scripts = self._storage.list_scripts()
        self._scripts = {}
        for script_id, payload in stored_scripts.items():
            try:
                self._scripts[script_id] = RegisteredScript.from_dict(payload)
            except (KeyError, TypeError, ValueError):
                continue

    def rescan(self) -> ScanResult:
        """Trigger a rescan of scripts and update registry."""

        if self._scanner is None:
            raise RuntimeError("Scanner is not configured for this registry")

        result = self._scanner.scan()

        previous_ids = set(self._scripts.keys())
        new_ids = {script.script_id for script in result.scripts}

        changed = False

        for scanned in result.scripts:
            existing = self._scripts.get(scanned.script_id)
            if existing is None:
                self._install_dependencies(scanned)
                registered = RegisteredScript(scanned, ScriptSettings())
                self._scripts[scanned.script_id] = registered
                self._persist_script(registered)
                changed = True
            elif existing.scanned.file_hash != scanned.file_hash:
                self._install_dependencies(scanned)
                updated = RegisteredScript(scanned, existing.settings)
                self._scripts[scanned.script_id] = updated
                self._persist_script(updated)
                changed = True

        removed_ids = previous_ids - new_ids
        for removed_id in removed_ids:
            del self._scripts[removed_id]
            try:
                self._storage.remove_script(removed_id)
            except KeyError:  # pragma: no cover - storage inconsistency
                pass
            changed = True

        if changed:
            self._notify_change()

        return result

    def get_script(self, script_id: str) -> RegisteredScript | None:
        """Retrieve metadata for a specific script."""

        return self._scripts.get(script_id)

    def list_scripts(self) -> dict[str, RegisteredScript]:
        """Return all registered scripts."""

        return dict(self._scripts)

    def list_enabled(self) -> dict[str, RegisteredScript]:
        """Return only enabled scripts."""

        return {sid: reg for sid, reg in self._scripts.items() if reg.enabled}

    def list_startup_scripts(self) -> dict[str, RegisteredScript]:
        """Return scripts configured to run at startup."""

        return {sid: reg for sid, reg in self._scripts.items() if reg.startup}

    def set_enabled(self, script_id: str, enabled: bool) -> None:
        """Enable or disable a script."""

        registered = self._scripts.get(script_id)
        if registered is None:
            raise KeyError(f"Script '{script_id}' is not registered")

        updated_settings = ScriptSettings(
            enabled=enabled,
            startup=registered.settings.startup,
            parameter_overrides=registered.settings.parameter_overrides,
        )
        updated = RegisteredScript(registered.scanned, updated_settings)
        self._scripts[script_id] = updated
        self._persist_script(updated)
        self._notify_change()

    def set_startup(self, script_id: str, startup: bool) -> None:
        """Configure whether a script should run at startup."""

        registered = self._scripts.get(script_id)
        if registered is None:
            raise KeyError(f"Script '{script_id}' is not registered")

        updated_settings = ScriptSettings(
            enabled=registered.settings.enabled,
            startup=startup,
            parameter_overrides=registered.settings.parameter_overrides,
        )
        updated = RegisteredScript(registered.scanned, updated_settings)
        self._scripts[script_id] = updated
        self._persist_script(updated)
        self._notify_change()

    def set_parameter_overrides(
        self,
        script_id: str,
        overrides: dict[str, Any],
    ) -> None:
        """Update parameter overrides for a script."""

        registered = self._scripts.get(script_id)
        if registered is None:
            raise KeyError(f"Script '{script_id}' is not registered")

        updated_settings = ScriptSettings(
            enabled=registered.settings.enabled,
            startup=registered.settings.startup,
            parameter_overrides=dict(overrides),
        )
        updated = RegisteredScript(registered.scanned, updated_settings)
        self._scripts[script_id] = updated
        self._persist_script(updated)
        self._notify_change()

    def query_by_category(self, category: str) -> dict[str, RegisteredScript]:
        """Query scripts by category."""

        return {
            sid: reg
            for sid, reg in self._scripts.items()
            if category in reg.scanned.categories
        }

    def query_by_group(self, group: tuple[str, ...]) -> dict[str, RegisteredScript]:
        """Query scripts by group hierarchy."""

        return {
            sid: reg
            for sid, reg in self._scripts.items()
            if reg.scanned.group == group or reg.scanned.group[: len(group)] == group
        }

    def query_by_service(self, service_id: str) -> dict[str, RegisteredScript]:
        """Query scripts related to a specific service."""

        return {
            sid: reg
            for sid, reg in self._scripts.items()
            if reg.scanned.related_service_id == service_id
        }

    def add_change_callback(self, callback: ChangeCallback) -> None:
        """Register a callback to be invoked when the registry changes."""

        self._callbacks.append(callback)

    def remove_change_callback(self, callback: ChangeCallback) -> None:
        """Unregister a previously registered callback."""

        try:
            self._callbacks.remove(callback)
        except ValueError:
            pass

    def _install_dependencies(self, scanned: ScannedScript) -> InstallResult | None:
        """Ensure dependencies declared by a scanned script are installed."""

        if self._dependency_installer is None:
            return None

        requirements = parse_requirements_from_docstring(scanned.docstring)
        if not requirements:
            logger.debug("No dependencies declared for script %s", scanned.script_id)
            return None

        result = self._dependency_installer.install_requirements(scanned.script_id, requirements)
        if result.successful():
            logger.debug(
                "Dependencies resolved for %s with status %s",
                scanned.script_id,
                result.status.value,
            )
        else:
            logger.warning(
                "Dependency installation failed for %s: %s",
                scanned.script_id,
                result.error_message or "unknown error",
            )
        return result

    def _persist_script(self, registered: RegisteredScript) -> None:
        payload = registered.to_dict()
        self._storage.save_script(registered.script_id, payload)

    def _notify_change(self) -> None:
        for callback in self._callbacks:
            try:
                callback()
            except Exception:  # pragma: no cover - user callback errors
                pass


__all__ = [
    "ScriptSettings",
    "RegisteredScript",
    "ScriptMetadataRegistry",
]
