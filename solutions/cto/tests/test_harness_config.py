"""Tests for configuration persistence using shared fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from contextipy.config.persistence import (
    LogStore,
    MenuVisibilityStore,
    ScriptParameterStore,
    ScriptRegistry,
)
from contextipy.config.settings import Settings, SettingsStore


class TestSettingsPersistence:
    """Test persistence of application settings."""

    def test_settings_round_trip(self, mock_home_dir: Path) -> None:
        """Test that settings can be saved and loaded from disk."""
        store = SettingsStore()
        settings = Settings(launch_on_startup=True, enable_notifications=False)
        store.save(settings)

        loaded = store.load()
        assert loaded == settings

    def test_settings_invalid_json(self, mock_home_dir: Path) -> None:
        """Test that invalid settings file falls back to defaults."""
        store = SettingsStore()
        settings_path = store.path
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text("not json", encoding="utf-8")

        loaded = store.load()
        assert loaded == Settings()


class TestScriptParameterStore:
    """Test parameter persistence for scripts."""

    def test_save_and_load_parameters(self, mock_home_dir: Path) -> None:
        """Test saving and loading script parameters."""
        store = ScriptParameterStore()
        params = {"script-1": {"threshold": 0.75, "enabled": True}}

        store.save_parameters(params)
        loaded = store.load_parameters()

        assert loaded == params

    def test_parameter_store_version_check(self, mock_home_dir: Path) -> None:
        """Test that newer versions raise an error."""
        store = ScriptParameterStore()
        store.path.parent.mkdir(parents=True, exist_ok=True)
        store.path.write_text(
            '{"version": 999, "payload": {}}',
            encoding="utf-8",
        )

        with pytest.raises(RuntimeError):
            store.load_parameters()


class TestMenuVisibilityStore:
    """Test menu visibility persistence."""

    def test_save_and_load_visibility(self, mock_home_dir: Path) -> None:
        """Test saving and loading menu visibility flags."""
        store = MenuVisibilityStore()
        flags = {"main": True, "secondary": False}

        store.save_flags(flags)
        loaded = store.load_flags()

        assert loaded == flags

    def test_visibility_normalizes_bool(self, mock_home_dir: Path) -> None:
        """Test that boolean values are normalized on load."""
        store = MenuVisibilityStore()
        store.save_flags({"main": 1, "secondary": 0})

        loaded = store.load_flags()
        assert loaded == {"main": True, "secondary": False}


class TestLogStore:
    """Test logging persistence."""

    def test_append_and_read_logs(self, mock_home_dir: Path) -> None:
        """Test appending to and reading from log store."""
        store = LogStore()
        store.append("first entry")
        store.append("second entry")

        entries = store.read()
        assert entries == ["first entry", "second entry"]


class TestScriptRegistry:
    """Test script registry persistence."""

    def test_registry_round_trip(self, mock_home_dir: Path) -> None:
        """Test saving, loading, and removing scripts."""
        registry = ScriptRegistry()
        payload = {"name": "Example", "entry": "script.py", "enabled": True}

        registry.save_script("script-1", payload)
        assert registry.load_script("script-1") == payload
        assert registry.list_scripts() == {"script-1": payload}

        registry.remove_script("script-1")
        assert registry.list_scripts() == {}

    def test_registry_schema_version(self, mock_home_dir: Path) -> None:
        """Test that schema version is reported."""
        registry = ScriptRegistry()
        assert registry.schema_version() == ScriptRegistry.SCHEMA_VERSION
