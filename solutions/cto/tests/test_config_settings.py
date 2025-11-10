"""Tests for contextipy.config.settings module."""

from __future__ import annotations

from pathlib import Path

from contextipy.config.settings import Settings, SettingsStore


class TestSettings:
    """Test Settings dataclass."""

    def test_defaults(self) -> None:
        settings = Settings()
        assert settings.launch_on_startup is False
        assert settings.enable_notifications is True

    def test_from_dict_with_all_fields(self) -> None:
        data = {"launch_on_startup": True, "enable_notifications": False}
        settings = Settings.from_dict(data)
        assert settings.launch_on_startup is True
        assert settings.enable_notifications is False

    def test_from_dict_with_partial_fields(self) -> None:
        settings = Settings.from_dict({"launch_on_startup": True})
        assert settings.launch_on_startup is True
        assert settings.enable_notifications is True

    def test_from_dict_with_extra_fields(self) -> None:
        data = {"launch_on_startup": True, "unknown_field": "value"}
        settings = Settings.from_dict(data)
        assert settings.launch_on_startup is True
        assert settings.enable_notifications is True

    def test_from_dict_empty(self) -> None:
        settings = Settings.from_dict({})
        assert settings.launch_on_startup is False
        assert settings.enable_notifications is True

    def test_to_dict(self) -> None:
        settings = Settings(launch_on_startup=True, enable_notifications=False)
        data = settings.to_dict()
        assert data == {"launch_on_startup": True, "enable_notifications": False}


class TestSettingsStore:
    """Test SettingsStore."""

    def test_load_nonexistent(self, tmp_path: Path) -> None:
        store = SettingsStore(path=tmp_path / "settings.json")
        settings = store.load()
        assert settings == Settings()

    def test_save_and_load(self, tmp_path: Path) -> None:
        store = SettingsStore(path=tmp_path / "settings.json")
        original = Settings(launch_on_startup=True, enable_notifications=False)

        store.save(original)
        loaded = store.load()

        assert loaded == original

    def test_save_creates_parent_directory(self, tmp_path: Path) -> None:
        path = tmp_path / "nested" / "dirs" / "settings.json"
        store = SettingsStore(path=path)
        settings = Settings()

        store.save(settings)
        assert path.exists()

    def test_load_invalid_json_returns_defaults(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        path.write_text("{invalid json}", encoding="utf-8")

        store = SettingsStore(path=path)
        settings = store.load()

        assert settings == Settings()

    def test_save_handles_oserror(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        store = SettingsStore(path=path)

        # Make directory read-only to trigger OSError
        path.parent.mkdir(parents=True, exist_ok=True)
        path.parent.chmod(0o400)

        settings = Settings(launch_on_startup=True)
        store.save(settings)

        # Restore permissions for cleanup
        path.parent.chmod(0o700)

        # Ensure settings file either doesn't exist or empty due to failed write
        assert not path.exists() or path.read_text(encoding="utf-8") == ""

    def test_on_change_notification(self, tmp_path: Path) -> None:
        store = SettingsStore(path=tmp_path / "settings.json")
        captured: list[Settings] = []

        def listener(settings: Settings) -> None:
            captured.append(settings)

        store.on_change(listener)

        settings1 = Settings(launch_on_startup=True)
        settings2 = Settings(enable_notifications=False)

        store.save(settings1)
        store.save(settings2)

        assert captured == [settings1, settings2]

    def test_remove_listener(self, tmp_path: Path) -> None:
        store = SettingsStore(path=tmp_path / "settings.json")
        captured: list[Settings] = []

        def listener(settings: Settings) -> None:
            captured.append(settings)

        store.on_change(listener)
        store.save(Settings())
        assert len(captured) == 1

        store.remove_listener(listener)
        store.save(Settings(launch_on_startup=True))
        assert len(captured) == 1

    def test_multiple_listeners(self, tmp_path: Path) -> None:
        store = SettingsStore(path=tmp_path / "settings.json")
        results1: list[Settings] = []
        results2: list[Settings] = []

        store.on_change(results1.append)
        store.on_change(results2.append)

        settings = Settings(launch_on_startup=True)
        store.save(settings)

        assert results1 == [settings]
        assert results2 == [settings]
