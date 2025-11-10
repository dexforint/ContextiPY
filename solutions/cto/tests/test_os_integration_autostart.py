"""Tests for OS integration autostart functionality."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from contextipy.os_integration.autostart import (
    AutostartResult,
    disable_autostart,
    enable_autostart,
    get_autostart_directory_linux,
    get_executable_path,
    is_autostart_enabled,
    is_linux,
    is_windows,
)


class TestPlatformDetection:
    """Test platform detection functions."""

    def test_get_executable_path(self) -> None:
        path = get_executable_path()
        assert isinstance(path, Path)
        assert path == Path(sys.executable)

    @patch("sys.platform", "win32")
    def test_is_windows_on_windows(self) -> None:
        assert is_windows() is True

    @patch("sys.platform", "linux")
    def test_is_windows_on_linux(self) -> None:
        assert is_windows() is False

    @patch("sys.platform", "linux")
    def test_is_linux_on_linux(self) -> None:
        assert is_linux() is True

    @patch("sys.platform", "win32")
    def test_is_linux_on_windows(self) -> None:
        assert is_linux() is False


class TestLinuxAutostart:
    """Test Linux autostart functionality."""

    def test_get_autostart_directory_uses_xdg_config_home(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
        directory = get_autostart_directory_linux()
        assert directory == Path("/custom/config/autostart")

    def test_get_autostart_directory_uses_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        directory = get_autostart_directory_linux()
        assert directory == Path.home() / ".config" / "autostart"

    @patch("contextipy.os_integration.autostart.is_linux", return_value=True)
    @patch("contextipy.os_integration.autostart.get_autostart_directory_linux")
    def test_enable_autostart_linux_success(
        self, mock_get_dir: Mock, mock_is_linux: Mock, tmp_path: Path
    ) -> None:
        autostart_dir = tmp_path / "autostart"
        mock_get_dir.return_value = autostart_dir

        result = enable_autostart(app_name="TestApp")

        assert result.success is True
        assert autostart_dir.exists()
        desktop_file = autostart_dir / "TestApp.desktop"
        assert desktop_file.exists()

        content = desktop_file.read_text()
        assert "Name=TestApp" in content
        assert "Type=Application" in content
        assert "X-GNOME-Autostart-enabled=true" in content

    @patch("contextipy.os_integration.autostart.is_linux", return_value=True)
    @patch("contextipy.os_integration.autostart.get_autostart_directory_linux")
    def test_enable_autostart_linux_with_command_args(
        self, mock_get_dir: Mock, mock_is_linux: Mock, tmp_path: Path
    ) -> None:
        autostart_dir = tmp_path / "autostart"
        mock_get_dir.return_value = autostart_dir

        result = enable_autostart(app_name="TestApp", command_args=["--tray", "--quiet"])

        assert result.success is True
        desktop_file = autostart_dir / "TestApp.desktop"
        content = desktop_file.read_text()
        assert "--tray" in content
        assert "--quiet" in content

    @patch("contextipy.os_integration.autostart.is_linux", return_value=True)
    @patch("contextipy.os_integration.autostart.get_autostart_directory_linux")
    def test_disable_autostart_linux_success(
        self, mock_get_dir: Mock, mock_is_linux: Mock, tmp_path: Path
    ) -> None:
        autostart_dir = tmp_path / "autostart"
        autostart_dir.mkdir(parents=True, exist_ok=True)
        mock_get_dir.return_value = autostart_dir

        desktop_file = autostart_dir / "TestApp.desktop"
        desktop_file.write_text("[Desktop Entry]\nName=TestApp\n")

        result = disable_autostart(app_name="TestApp")

        assert result.success is True
        assert not desktop_file.exists()

    @patch("contextipy.os_integration.autostart.is_linux", return_value=True)
    @patch("contextipy.os_integration.autostart.get_autostart_directory_linux")
    def test_disable_autostart_linux_not_enabled(
        self, mock_get_dir: Mock, mock_is_linux: Mock, tmp_path: Path
    ) -> None:
        autostart_dir = tmp_path / "autostart"
        mock_get_dir.return_value = autostart_dir

        result = disable_autostart(app_name="TestApp")

        assert result.success is True
        assert "not enabled" in result.message.lower()

    @patch("contextipy.os_integration.autostart.is_linux", return_value=True)
    @patch("contextipy.os_integration.autostart.get_autostart_directory_linux")
    def test_is_autostart_enabled_linux_true(
        self, mock_get_dir: Mock, mock_is_linux: Mock, tmp_path: Path
    ) -> None:
        autostart_dir = tmp_path / "autostart"
        autostart_dir.mkdir(parents=True, exist_ok=True)
        mock_get_dir.return_value = autostart_dir

        desktop_file = autostart_dir / "TestApp.desktop"
        desktop_file.write_text("[Desktop Entry]\nName=TestApp\n")

        result = is_autostart_enabled(app_name="TestApp")
        assert result is True

    @patch("contextipy.os_integration.autostart.is_linux", return_value=True)
    @patch("contextipy.os_integration.autostart.get_autostart_directory_linux")
    def test_is_autostart_enabled_linux_false(
        self, mock_get_dir: Mock, mock_is_linux: Mock, tmp_path: Path
    ) -> None:
        autostart_dir = tmp_path / "autostart"
        mock_get_dir.return_value = autostart_dir

        result = is_autostart_enabled(app_name="TestApp")
        assert result is False


class TestWindowsAutostart:
    """Test Windows autostart functionality."""

    @patch("contextipy.os_integration.autostart.is_windows", return_value=True)
    def test_enable_autostart_windows_success(self, mock_is_windows: Mock) -> None:
        mock_winreg = MagicMock()
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value = mock_key
        mock_winreg.HKEY_CURRENT_USER = 0x80000001
        mock_winreg.KEY_WRITE = 0x20006
        mock_winreg.REG_SZ = 1

        with patch.dict("sys.modules", {"winreg": mock_winreg}):
            result = enable_autostart(app_name="TestApp")

        assert result.success is True
        mock_winreg.SetValueEx.assert_called_once()
        call_args = mock_winreg.SetValueEx.call_args
        assert call_args[0][1] == "TestApp"

    @patch("contextipy.os_integration.autostart.is_windows", return_value=True)
    def test_enable_autostart_windows_with_command_args(self, mock_is_windows: Mock) -> None:
        mock_winreg = MagicMock()
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value = mock_key
        mock_winreg.HKEY_CURRENT_USER = 0x80000001
        mock_winreg.KEY_WRITE = 0x20006
        mock_winreg.REG_SZ = 1

        with patch.dict("sys.modules", {"winreg": mock_winreg}):
            result = enable_autostart(app_name="TestApp", command_args=["--tray"])

        assert result.success is True
        call_args = mock_winreg.SetValueEx.call_args
        command_line = call_args[0][3]
        assert "--tray" in command_line

    @patch("contextipy.os_integration.autostart.is_windows", return_value=True)
    def test_disable_autostart_windows_success(self, mock_is_windows: Mock) -> None:
        mock_winreg = MagicMock()
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value = mock_key
        mock_winreg.HKEY_CURRENT_USER = 0x80000001
        mock_winreg.KEY_WRITE = 0x20006

        with patch.dict("sys.modules", {"winreg": mock_winreg}):
            result = disable_autostart(app_name="TestApp")

        assert result.success is True
        mock_winreg.DeleteValue.assert_called_once_with(mock_key, "TestApp")

    @patch("contextipy.os_integration.autostart.is_windows", return_value=True)
    def test_disable_autostart_windows_not_enabled(self, mock_is_windows: Mock) -> None:
        mock_winreg = MagicMock()
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value = mock_key
        mock_winreg.DeleteValue.side_effect = FileNotFoundError()
        mock_winreg.HKEY_CURRENT_USER = 0x80000001
        mock_winreg.KEY_WRITE = 0x20006

        with patch.dict("sys.modules", {"winreg": mock_winreg}):
            result = disable_autostart(app_name="TestApp")

        assert result.success is True
        assert "not enabled" in result.message.lower()

    @patch("contextipy.os_integration.autostart.is_windows", return_value=True)
    def test_is_autostart_enabled_windows_true(self, mock_is_windows: Mock) -> None:
        mock_winreg = MagicMock()
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value = mock_key
        mock_winreg.QueryValueEx.return_value = ("some_value", 1)
        mock_winreg.HKEY_CURRENT_USER = 0x80000001
        mock_winreg.KEY_READ = 0x20019

        with patch.dict("sys.modules", {"winreg": mock_winreg}):
            result = is_autostart_enabled(app_name="TestApp")

        assert result is True

    @patch("contextipy.os_integration.autostart.is_windows", return_value=True)
    def test_is_autostart_enabled_windows_false(self, mock_is_windows: Mock) -> None:
        mock_winreg = MagicMock()
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value = mock_key
        mock_winreg.QueryValueEx.side_effect = FileNotFoundError()
        mock_winreg.HKEY_CURRENT_USER = 0x80000001
        mock_winreg.KEY_READ = 0x20019

        with patch.dict("sys.modules", {"winreg": mock_winreg}):
            result = is_autostart_enabled(app_name="TestApp")

        assert result is False

    @patch("contextipy.os_integration.autostart.is_windows", return_value=True)
    def test_enable_autostart_windows_registry_error(self, mock_is_windows: Mock) -> None:
        mock_winreg = MagicMock()
        mock_winreg.OpenKey.side_effect = OSError("Registry error")
        mock_winreg.HKEY_CURRENT_USER = 0x80000001
        mock_winreg.KEY_WRITE = 0x20006

        with patch.dict("sys.modules", {"winreg": mock_winreg}):
            result = enable_autostart(app_name="TestApp")

        assert result.success is False
        assert "Registry operation failed" in result.error


class TestUnsupportedPlatform:
    """Test behavior on unsupported platforms."""

    @patch("contextipy.os_integration.autostart.is_windows", return_value=False)
    @patch("contextipy.os_integration.autostart.is_linux", return_value=False)
    def test_enable_autostart_unsupported_platform(
        self, mock_is_linux: Mock, mock_is_windows: Mock
    ) -> None:
        result = enable_autostart()
        assert result.success is False
        assert "only supported on Windows and Linux" in result.error

    @patch("contextipy.os_integration.autostart.is_windows", return_value=False)
    @patch("contextipy.os_integration.autostart.is_linux", return_value=False)
    def test_disable_autostart_unsupported_platform(
        self, mock_is_linux: Mock, mock_is_windows: Mock
    ) -> None:
        result = disable_autostart()
        assert result.success is False
        assert "only supported on Windows and Linux" in result.error

    @patch("contextipy.os_integration.autostart.is_windows", return_value=False)
    @patch("contextipy.os_integration.autostart.is_linux", return_value=False)
    def test_is_autostart_enabled_unsupported_platform(
        self, mock_is_linux: Mock, mock_is_windows: Mock
    ) -> None:
        result = is_autostart_enabled()
        assert result is False


class TestAutostartResult:
    """Test AutostartResult dataclass."""

    def test_success_result(self) -> None:
        result = AutostartResult(success=True, message="Success!")
        assert result.success is True
        assert result.message == "Success!"
        assert result.error is None

    def test_error_result(self) -> None:
        result = AutostartResult(success=False, error="Failed!")
        assert result.success is False
        assert result.error == "Failed!"
        assert result.message is None
