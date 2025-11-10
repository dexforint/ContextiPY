"""Tests for contextipy.config.paths module."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from contextipy.config import paths


@pytest.fixture
def clean_env() -> dict[str, Any]:
    """Return a clean environment for testing."""
    return {}


@pytest.fixture
def temp_home(tmp_path: Path) -> Path:
    """Create a temporary home directory."""
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    return home


class TestGetConfigRoot:
    """Test get_config_root platform behavior."""

    def test_windows_with_appdata(self, clean_env: dict[str, Any]) -> None:
        clean_env["APPDATA"] = "C:\\Users\\Test\\AppData\\Roaming"
        with (
            patch("platform.system", return_value="Windows"),
            patch.dict(os.environ, clean_env, clear=True),
            patch("contextipy.config.paths.ensure_directory", side_effect=lambda p: p),
        ):
            result = paths.get_config_root()
            expected = Path("C:\\Users\\Test\\AppData\\Roaming") / "contextipy"
            assert result == expected

    def test_windows_without_appdata(self, temp_home: Path) -> None:
        with (
            patch("platform.system", return_value="Windows"),
            patch.dict(os.environ, {}, clear=True),
            patch("pathlib.Path.home", return_value=temp_home),
            patch("contextipy.config.paths.ensure_directory", side_effect=lambda p: p),
        ):
            result = paths.get_config_root()
            assert result == temp_home / "AppData" / "Roaming" / "contextipy"

    def test_darwin(self, temp_home: Path) -> None:
        with (
            patch("platform.system", return_value="Darwin"),
            patch.dict(os.environ, {}, clear=True),
            patch("pathlib.Path.home", return_value=temp_home),
            patch("contextipy.config.paths.ensure_directory", side_effect=lambda p: p),
        ):
            result = paths.get_config_root()
            assert result == temp_home / "Library" / "Application Support" / "contextipy"

    def test_linux_with_xdg_config_home(self, clean_env: dict[str, Any]) -> None:
        clean_env["XDG_CONFIG_HOME"] = "/home/testuser/.config"
        with (
            patch("platform.system", return_value="Linux"),
            patch.dict(os.environ, clean_env, clear=True),
            patch("contextipy.config.paths.ensure_directory", side_effect=lambda p: p),
        ):
            result = paths.get_config_root()
            assert result == Path("/home/testuser/.config/contextipy")

    def test_linux_without_xdg(self, temp_home: Path) -> None:
        with (
            patch("platform.system", return_value="Linux"),
            patch.dict(os.environ, {}, clear=True),
            patch("pathlib.Path.home", return_value=temp_home),
            patch("contextipy.config.paths.ensure_directory", side_effect=lambda p: p),
        ):
            result = paths.get_config_root()
            assert result == temp_home / ".config" / "contextipy"


class TestGetDataRoot:
    """Test get_data_root platform behavior."""

    def test_windows_with_localappdata(self, clean_env: dict[str, Any]) -> None:
        clean_env["LOCALAPPDATA"] = "C:\\Users\\Test\\AppData\\Local"
        with (
            patch("platform.system", return_value="Windows"),
            patch.dict(os.environ, clean_env, clear=True),
            patch("contextipy.config.paths.ensure_directory", side_effect=lambda p: p),
        ):
            result = paths.get_data_root()
            expected = Path("C:\\Users\\Test\\AppData\\Local") / "contextipy"
            assert result == expected

    def test_windows_fallback_to_appdata(self, clean_env: dict[str, Any]) -> None:
        clean_env["APPDATA"] = "C:\\Users\\Test\\AppData\\Roaming"
        with (
            patch("platform.system", return_value="Windows"),
            patch.dict(os.environ, clean_env, clear=True),
            patch("contextipy.config.paths.ensure_directory", side_effect=lambda p: p),
        ):
            result = paths.get_data_root()
            expected = Path("C:\\Users\\Test\\AppData\\Roaming") / "contextipy"
            assert result == expected

    def test_windows_without_env_vars(self, temp_home: Path) -> None:
        with (
            patch("platform.system", return_value="Windows"),
            patch.dict(os.environ, {}, clear=True),
            patch("pathlib.Path.home", return_value=temp_home),
            patch("contextipy.config.paths.ensure_directory", side_effect=lambda p: p),
        ):
            result = paths.get_data_root()
            assert result == temp_home / "AppData" / "Local" / "contextipy"

    def test_darwin(self, temp_home: Path) -> None:
        with (
            patch("platform.system", return_value="Darwin"),
            patch.dict(os.environ, {}, clear=True),
            patch("pathlib.Path.home", return_value=temp_home),
            patch("contextipy.config.paths.ensure_directory", side_effect=lambda p: p),
        ):
            result = paths.get_data_root()
            assert result == temp_home / "Library" / "Application Support" / "contextipy"

    def test_linux_with_xdg_data_home(self, clean_env: dict[str, Any]) -> None:
        clean_env["XDG_DATA_HOME"] = "/home/testuser/.local/share"
        with (
            patch("platform.system", return_value="Linux"),
            patch.dict(os.environ, clean_env, clear=True),
            patch("contextipy.config.paths.ensure_directory", side_effect=lambda p: p),
        ):
            result = paths.get_data_root()
            assert result == Path("/home/testuser/.local/share/contextipy")

    def test_linux_without_xdg(self, temp_home: Path) -> None:
        with (
            patch("platform.system", return_value="Linux"),
            patch.dict(os.environ, {}, clear=True),
            patch("pathlib.Path.home", return_value=temp_home),
            patch("contextipy.config.paths.ensure_directory", side_effect=lambda p: p),
        ):
            result = paths.get_data_root()
            assert result == temp_home / ".local" / "share" / "contextipy"


class TestGetLogsDir:
    """Test get_logs_dir platform behavior."""

    def test_darwin(self, temp_home: Path) -> None:
        with (
            patch("platform.system", return_value="Darwin"),
            patch.dict(os.environ, {}, clear=True),
            patch("pathlib.Path.home", return_value=temp_home),
            patch("contextipy.config.paths.ensure_directory", side_effect=lambda p: p),
        ):
            result = paths.get_logs_dir()
            assert result == temp_home / "Library" / "Logs" / "contextipy"

    def test_windows(self, clean_env: dict[str, Any]) -> None:
        clean_env["LOCALAPPDATA"] = "C:\\Users\\Test\\AppData\\Local"
        with (
            patch("platform.system", return_value="Windows"),
            patch.dict(os.environ, clean_env, clear=True),
            patch("contextipy.config.paths.ensure_directory", side_effect=lambda p: p),
        ):
            result = paths.get_logs_dir()
            expected = Path("C:\\Users\\Test\\AppData\\Local") / "contextipy" / "logs"
            assert result == expected

    def test_linux(self, temp_home: Path) -> None:
        with (
            patch("platform.system", return_value="Linux"),
            patch.dict(os.environ, {}, clear=True),
            patch("pathlib.Path.home", return_value=temp_home),
            patch("contextipy.config.paths.ensure_directory", side_effect=lambda p: p),
        ):
            result = paths.get_logs_dir()
            assert result == temp_home / ".local" / "share" / "contextipy" / "logs"


class TestEnsureDirectory:
    """Test ensure_directory function."""

    def test_creates_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "nested" / "dir" / "structure"
        result = paths.ensure_directory(target)
        assert result == target
        assert target.exists()
        assert target.is_dir()

    def test_existing_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "existing"
        target.mkdir()
        result = paths.ensure_directory(target)
        assert result == target
        assert target.exists()


class TestPathGetters:
    """Test convenience path getter functions."""

    def test_get_settings_path(self, tmp_path: Path) -> None:
        with (
            patch("platform.system", return_value="Linux"),
            patch.dict(os.environ, {}, clear=True),
            patch("pathlib.Path.home", return_value=tmp_path),
            patch("contextipy.config.paths.ensure_directory", side_effect=lambda p: p),
        ):
            result = paths.get_settings_path()
            assert result == tmp_path / ".config" / "contextipy" / "settings.json"

    def test_get_parameters_path(self, tmp_path: Path) -> None:
        with (
            patch("platform.system", return_value="Linux"),
            patch.dict(os.environ, {}, clear=True),
            patch("pathlib.Path.home", return_value=tmp_path),
            patch("contextipy.config.paths.ensure_directory", side_effect=lambda p: p),
        ):
            result = paths.get_parameters_path()
            assert result == tmp_path / ".local" / "share" / "contextipy" / "parameters.json"

    def test_get_menu_visibility_path(self, tmp_path: Path) -> None:
        with (
            patch("platform.system", return_value="Linux"),
            patch.dict(os.environ, {}, clear=True),
            patch("pathlib.Path.home", return_value=tmp_path),
            patch("contextipy.config.paths.ensure_directory", side_effect=lambda p: p),
        ):
            result = paths.get_menu_visibility_path()
            assert result == tmp_path / ".local" / "share" / "contextipy" / "menu_visibility.json"

    def test_get_registry_path(self, tmp_path: Path) -> None:
        with (
            patch("platform.system", return_value="Linux"),
            patch.dict(os.environ, {}, clear=True),
            patch("pathlib.Path.home", return_value=tmp_path),
            patch("contextipy.config.paths.ensure_directory", side_effect=lambda p: p),
        ):
            result = paths.get_registry_path()
            assert result == tmp_path / ".local" / "share" / "contextipy" / "registry.db"
