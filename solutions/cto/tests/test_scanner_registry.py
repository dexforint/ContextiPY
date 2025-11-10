"""Tests for the script registry module."""

from pathlib import Path
from typing import Any

import pytest

from contextipy.config.persistence import ScriptRegistry
from contextipy.scanner import ScriptScanner
from contextipy.scanner.registry import (
    RegisteredScript,
    ScriptMetadataRegistry,
    ScriptSettings,
)


@pytest.fixture
def fixtures_path() -> Path:
    """Return the path to the test fixtures directory."""

    return Path(__file__).parent / "fixtures" / "scripts"


@pytest.fixture
def registry_db(tmp_path: Path) -> ScriptRegistry:
    """Create a temporary script registry database."""

    return ScriptRegistry(tmp_path / "test_registry.db")


@pytest.fixture
def scanner(fixtures_path: Path) -> ScriptScanner:
    """Create a script scanner for fixtures."""

    return ScriptScanner(fixtures_path)


@pytest.fixture
def registry(registry_db: ScriptRegistry, scanner: ScriptScanner) -> ScriptMetadataRegistry:
    """Create a script metadata registry."""

    return ScriptMetadataRegistry(storage=registry_db, scanner=scanner)


class TestScriptSettings:
    """Tests for ScriptSettings dataclass."""

    def test_default_settings(self) -> None:
        settings = ScriptSettings()
        assert settings.enabled is True
        assert settings.startup is False
        assert settings.parameter_overrides is None

    def test_to_dict(self) -> None:
        settings = ScriptSettings(
            enabled=False,
            startup=True,
            parameter_overrides={"param1": "value1"},
        )
        data = settings.to_dict()
        assert data["enabled"] is False
        assert data["startup"] is True
        assert data["parameter_overrides"] == {"param1": "value1"}

    def test_from_dict(self) -> None:
        data: dict[str, Any] = {
            "enabled": False,
            "startup": True,
            "parameter_overrides": {"param1": "value1"},
        }
        settings = ScriptSettings.from_dict(data)
        assert settings.enabled is False
        assert settings.startup is True
        assert settings.parameter_overrides == {"param1": "value1"}

    def test_from_dict_defaults(self) -> None:
        settings = ScriptSettings.from_dict({})
        assert settings.enabled is True
        assert settings.startup is False
        assert settings.parameter_overrides is None


class TestScriptMetadataRegistry:
    """Tests for ScriptMetadataRegistry."""

    def test_initial_rescan(self, registry: ScriptMetadataRegistry) -> None:
        result = registry.rescan()
        assert result.successful()
        assert len(result.scripts) > 0

    def test_get_script(self, registry: ScriptMetadataRegistry) -> None:
        registry.rescan()
        script = registry.get_script("simple_test")
        assert script is not None
        assert script.script_id == "simple_test"
        assert script.enabled is True

    def test_get_nonexistent_script(self, registry: ScriptMetadataRegistry) -> None:
        registry.rescan()
        script = registry.get_script("nonexistent")
        assert script is None

    def test_list_scripts(self, registry: ScriptMetadataRegistry) -> None:
        registry.rescan()
        scripts = registry.list_scripts()
        assert len(scripts) > 0
        assert "simple_test" in scripts

    def test_set_enabled(self, registry: ScriptMetadataRegistry) -> None:
        registry.rescan()
        registry.set_enabled("simple_test", False)
        script = registry.get_script("simple_test")
        assert script is not None
        assert script.enabled is False

    def test_set_enabled_nonexistent(self, registry: ScriptMetadataRegistry) -> None:
        registry.rescan()
        with pytest.raises(KeyError):
            registry.set_enabled("nonexistent", False)

    def test_set_startup(self, registry: ScriptMetadataRegistry) -> None:
        registry.rescan()
        registry.set_startup("simple_test", True)
        script = registry.get_script("simple_test")
        assert script is not None
        assert script.startup is True

    def test_set_startup_nonexistent(self, registry: ScriptMetadataRegistry) -> None:
        registry.rescan()
        with pytest.raises(KeyError):
            registry.set_startup("nonexistent", True)

    def test_set_parameter_overrides(self, registry: ScriptMetadataRegistry) -> None:
        registry.rescan()
        overrides = {"width": 100, "height": 200}
        registry.set_parameter_overrides("resize_image", overrides)
        script = registry.get_script("resize_image")
        assert script is not None
        assert script.settings.parameter_overrides == overrides

    def test_list_enabled(self, registry: ScriptMetadataRegistry) -> None:
        registry.rescan()
        registry.set_enabled("simple_test", False)
        enabled = registry.list_enabled()
        assert "simple_test" not in enabled
        assert len(enabled) < len(registry.list_scripts())

    def test_list_startup_scripts(self, registry: ScriptMetadataRegistry) -> None:
        registry.rescan()
        registry.set_startup("simple_test", True)
        registry.set_startup("text_to_upper", True)
        startup = registry.list_startup_scripts()
        assert "simple_test" in startup
        assert "text_to_upper" in startup

    def test_query_by_category(self, registry: ScriptMetadataRegistry) -> None:
        registry.rescan()
        test_scripts = registry.query_by_category("test")
        assert len(test_scripts) > 0
        assert "simple_test" in test_scripts

    def test_query_by_group(self, registry: ScriptMetadataRegistry) -> None:
        registry.rescan()
        utilities = registry.query_by_group(("utilities",))
        assert len(utilities) >= 2
        script_ids = {s.script_id for s in utilities.values()}
        assert "text_to_upper" in script_ids
        assert "text_to_lower" in script_ids

    def test_query_by_service(self, registry: ScriptMetadataRegistry) -> None:
        registry.rescan()
        service_scripts = registry.query_by_service("example_service")
        assert len(service_scripts) > 0
        assert "service_script_example" in service_scripts

    def test_persistence(
        self,
        registry_db: ScriptRegistry,
        scanner: ScriptScanner,
    ) -> None:
        registry1 = ScriptMetadataRegistry(storage=registry_db, scanner=scanner)
        registry1.rescan()
        registry1.set_enabled("simple_test", False)
        registry1.set_startup("text_to_upper", True)

        registry2 = ScriptMetadataRegistry(storage=registry_db, scanner=scanner)
        registry2.load()
        script1 = registry2.get_script("simple_test")
        script2 = registry2.get_script("text_to_upper")
        assert script1 is not None
        assert script1.enabled is False
        assert script2 is not None
        assert script2.startup is True

    def test_rescan_detects_changes(
        self,
        tmp_path: Path,
        registry_db: ScriptRegistry,
    ) -> None:
        script_dir = tmp_path / "scripts"
        script_dir.mkdir()
        script_file = script_dir / "test_script.py"
        script_file.write_text(
            """
from contextipy import oneshot_script

@oneshot_script(script_id="test", title="Test", description="Test script")
def test_func() -> str:
    return "test"
"""
        )

        scanner = ScriptScanner(script_dir)
        registry = ScriptMetadataRegistry(storage=registry_db, scanner=scanner)
        result1 = registry.rescan()
        script1 = registry.get_script("test")
        assert script1 is not None
        hash1 = script1.scanned.file_hash

        script_file.write_text(
            """
from contextipy import oneshot_script

@oneshot_script(script_id="test", title="Test", description="Modified")
def test_func() -> str:
    return "modified"
"""
        )

        result2 = registry.rescan()
        script2 = registry.get_script("test")
        assert script2 is not None
        hash2 = script2.scanned.file_hash
        assert hash1 != hash2
        assert script2.scanned.description == "Modified"

    def test_rescan_removes_deleted_scripts(
        self,
        tmp_path: Path,
        registry_db: ScriptRegistry,
    ) -> None:
        script_dir = tmp_path / "scripts"
        script_dir.mkdir()
        script_file = script_dir / "test_script.py"
        script_file.write_text(
            """
from contextipy import oneshot_script

@oneshot_script(script_id="test", title="Test", description="Test script")
def test_func() -> str:
    return "test"
"""
        )

        scanner = ScriptScanner(script_dir)
        registry = ScriptMetadataRegistry(storage=registry_db, scanner=scanner)
        registry.rescan()
        assert registry.get_script("test") is not None

        script_file.unlink()
        registry.rescan()
        assert registry.get_script("test") is None

    def test_change_callbacks(self, registry: ScriptMetadataRegistry) -> None:
        callback_count = 0

        def callback() -> None:
            nonlocal callback_count
            callback_count += 1

        registry.add_change_callback(callback)
        registry.rescan()
        assert callback_count == 1

        registry.set_enabled("simple_test", False)
        assert callback_count == 2

    def test_remove_change_callback(self, registry: ScriptMetadataRegistry) -> None:
        callback_count = 0

        def callback() -> None:
            nonlocal callback_count
            callback_count += 1

        registry.add_change_callback(callback)
        registry.rescan()
        assert callback_count == 1

        registry.remove_change_callback(callback)
        registry.set_enabled("simple_test", False)
        assert callback_count == 1

    def test_scanner_not_configured(self, registry_db: ScriptRegistry) -> None:
        registry = ScriptMetadataRegistry(storage=registry_db)
        with pytest.raises(RuntimeError):
            registry.rescan()


class TestRegisteredScript:
    """Tests for RegisteredScript serialization."""

    def test_serialization_roundtrip(self, registry: ScriptMetadataRegistry) -> None:
        registry.rescan()
        registry.set_enabled("simple_test", False)
        registry.set_startup("simple_test", True)
        original = registry.get_script("simple_test")
        assert original is not None

        data = original.to_dict()
        restored = RegisteredScript.from_dict(data)
        assert restored.script_id == original.script_id
        assert restored.enabled == original.enabled
        assert restored.startup == original.startup
        assert restored.scanned.file_hash == original.scanned.file_hash
