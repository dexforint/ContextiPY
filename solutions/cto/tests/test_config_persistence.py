"""Tests for contextipy.config.settings and contextipy.config.persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from contextipy.config.persistence import (
    LogStore,
    MenuVisibilityStore,
    ScriptParameterStore,
    ScriptRegistry,
)
from contextipy.config.settings import Settings, SettingsStore


def test_settings_store_round_trip(tmp_path: Path) -> None:
    settings_path = tmp_path / "config" / "settings.json"
    store = SettingsStore(path=settings_path)

    captured: list[Settings] = []
    store.on_change(captured.append)

    settings = Settings(launch_on_startup=True, enable_notifications=False)
    store.save(settings)

    assert settings_path.exists()
    assert captured == [settings]

    loaded = store.load()
    assert loaded == settings


def test_settings_store_handles_corrupt_file(tmp_path: Path) -> None:
    settings_path = tmp_path / "config" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text("not json", encoding="utf-8")

    store = SettingsStore(path=settings_path)
    loaded = store.load()
    assert loaded == Settings()


def test_script_parameter_store_round_trip(tmp_path: Path) -> None:
    store = ScriptParameterStore(path=tmp_path / "data" / "params.json")
    payload = {"script-1": {"threshold": 5, "enabled": True}}

    store.save_parameters(payload)

    raw = json.loads(store.path.read_text(encoding="utf-8"))
    assert raw["version"] == ScriptParameterStore.VERSION
    assert raw["payload"] == payload

    loaded = store.load_parameters()
    assert loaded == payload


def test_script_parameter_store_newer_version(tmp_path: Path) -> None:
    store = ScriptParameterStore(path=tmp_path / "data" / "params.json")
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(
        json.dumps({"version": ScriptParameterStore.VERSION + 1, "payload": {}}),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError):
        store.load_parameters()


def test_menu_visibility_store_bool_normalization(tmp_path: Path) -> None:
    store = MenuVisibilityStore(path=tmp_path / "data" / "visibility.json")
    flags = {"main": 1, "secondary": False}

    store.save_flags(flags)
    loaded = store.load_flags()

    assert loaded == {"main": True, "secondary": False}


def test_log_store_append_and_read(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    store = LogStore(directory=log_dir)
    store.append("first entry")
    store.append("second entry")

    assert store.path.exists()
    assert store.read() == ["first entry", "second entry"]


def test_script_registry_round_trip(tmp_path: Path) -> None:
    registry_path = tmp_path / "data" / "registry.db"
    registry = ScriptRegistry(path=registry_path)

    payload = {"name": "Sample Script", "entry": "script.py", "enabled": True}
    registry.save_script("script-1", payload)

    assert registry.schema_version() == ScriptRegistry.SCHEMA_VERSION
    assert registry.load_script("script-1") == payload
    assert registry.list_scripts() == {"script-1": payload}

    registry.remove_script("script-1")
    with pytest.raises(KeyError):
        registry.load_script("script-1")

    assert registry.list_scripts() == {}


def test_script_registry_persists_to_disk(tmp_path: Path) -> None:
    registry_path = tmp_path / "data" / "registry.db"
    registry = ScriptRegistry(path=registry_path)
    registry.save_script("script-1", {"value": 1})

    assert registry_path.exists()

    registry_reopened = ScriptRegistry(path=registry_path)
    assert registry_reopened.load_script("script-1") == {"value": 1}
