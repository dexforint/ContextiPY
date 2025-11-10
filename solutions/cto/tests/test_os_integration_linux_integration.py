"""Tests for Linux file manager integration via desktop actions."""

import os
import stat
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from contextipy.os_integration.linux_integration import (
    DesktopAction,
    RegistrationResult,
    actions_from_scripts,
    build_command_line,
    cleanup_removed_scripts,
    get_actions_directory,
    get_contextipy_executable,
    get_scripts_directory,
    is_linux,
    register_file_manager_actions,
    unregister_file_manager_actions,
    update_file_manager_actions_on_scan,
    update_file_manager_actions_visibility,
)


@pytest.fixture
def temp_home(tmp_path: Path) -> Path:
    """Provide a temporary home directory for testing."""

    home = tmp_path / "home"
    home.mkdir()
    return home


@pytest.fixture
def mock_linux_platform() -> Any:
    """Force the module to think it is running on Linux."""

    with patch("contextipy.os_integration.linux_integration.sys.platform", "linux"):
        with patch(
            "contextipy.os_integration.linux_integration.platform.system",
            return_value="Linux",
        ):
            yield


@contextmanager
def patched_home_env(home: Path, extra_env: dict[str, str] | None = None, *, clear: bool = False):
    """Patch environment variables and Path.home() for tests."""

    env_vars = {"HOME": str(home)}
    if extra_env:
        env_vars.update(extra_env)
    with patch("contextipy.os_integration.linux_integration.Path.home", return_value=home):
        with patch.dict("os.environ", env_vars, clear=clear):
            yield


class TestPlatformDetection:
    """Ensure platform helpers behave as expected."""

    def test_is_linux_on_linux(self, mock_linux_platform: Any) -> None:
        assert is_linux() is True

    def test_is_linux_on_windows(self) -> None:
        with patch("contextipy.os_integration.linux_integration.sys.platform", "win32"):
            with patch(
                "contextipy.os_integration.linux_integration.platform.system",
                return_value="Windows",
            ):
                assert is_linux() is False

    def test_is_linux_on_darwin(self) -> None:
        with patch("contextipy.os_integration.linux_integration.sys.platform", "darwin"):
            with patch(
                "contextipy.os_integration.linux_integration.platform.system",
                return_value="Darwin",
            ):
                assert is_linux() is False


class TestPathHelpers:
    """Validate path resolution helpers."""

    def test_get_actions_directory_default(self, temp_home: Path) -> None:
        with patched_home_env(temp_home, clear=True):
            actions_dir = get_actions_directory()
            assert actions_dir == temp_home / ".local" / "share" / "file-manager" / "actions"

    def test_get_actions_directory_xdg(self, temp_home: Path) -> None:
        xdg_data = temp_home / "xdg-data"
        with patched_home_env(temp_home, {"XDG_DATA_HOME": str(xdg_data)}, clear=True):
            actions_dir = get_actions_directory()
            assert actions_dir == xdg_data / "file-manager" / "actions"

    def test_get_scripts_directory_default(self, temp_home: Path) -> None:
        with patched_home_env(temp_home, clear=True):
            scripts_dir = get_scripts_directory()
            assert scripts_dir == temp_home / ".local" / "share" / "contextipy" / "scripts"

    def test_get_scripts_directory_xdg(self, temp_home: Path) -> None:
        xdg_data = temp_home / "xdg-data"
        with patched_home_env(temp_home, {"XDG_DATA_HOME": str(xdg_data)}, clear=True):
            scripts_dir = get_scripts_directory()
            assert scripts_dir == xdg_data / "contextipy" / "scripts"


class TestCommandLineHelpers:
    """Validate command line helpers."""

    def test_build_command_line_custom_executable(self) -> None:
        python_exe = Path("/usr/bin/python3")
        command = build_command_line("pkg.module", "func", "script", python_exe)
        assert str(python_exe) in command
        assert "-m" in command
        assert "contextipy.execution.context_entry" in command
        assert '"pkg.module:func"' in command
        assert '--files "$@"' in command

    def test_build_command_line_defaults(self) -> None:
        command = build_command_line("pkg.module", "func", "script")
        assert "contextipy.execution.context_entry" in command

    def test_get_contextipy_executable(self) -> None:
        assert isinstance(get_contextipy_executable(), Path)


class TestDataclasses:
    """Basic smoke tests for data containers."""

    def test_desktop_action_defaults(self) -> None:
        action = DesktopAction("id", "Title", "python script.py")
        assert action.group == ()
        assert action.icon is None
        assert action.accepts == ()

    def test_registration_result_defaults(self) -> None:
        result = RegistrationResult(True)
        assert result.success is True
        assert result.message is None
        assert result.error is None


class TestActionsFromScripts:
    """Verify conversion from metadata objects."""

    def test_scanned_script(self) -> None:
        script = Mock()
        script.script_id = "script"
        script.module = "pkg"
        script.qualname = "pkg:func"
        script.title = "Title"
        script.group = ("Utilities",)
        script.icon = "icon.png"
        script.accepts = ("file",)

        actions = actions_from_scripts([script])
        assert len(actions) == 1
        assert actions[0].script_id == "script"
        assert actions[0].group == ("Utilities",)
        assert actions[0].icon == "icon.png"
        assert actions[0].accepts == ("file",)

    def test_registered_script(self) -> None:
        scanned = Mock()
        scanned.script_id = "script"
        scanned.module = "pkg"
        scanned.qualname = "pkg:func"
        scanned.title = "Title"
        scanned.group = ()
        scanned.icon = None
        scanned.accepts = ()

        registered = Mock()
        registered.scanned = scanned

        actions = actions_from_scripts([registered])
        assert len(actions) == 1
        assert actions[0].script_id == "script"


class TestRegisterFileManagerActions:
    """Exercise the registration workflow."""

    def test_requires_linux(self, temp_home: Path) -> None:
        with patch("contextipy.os_integration.linux_integration.is_linux", return_value=False):
            result = register_file_manager_actions([DesktopAction("id", "Title", "cmd")])
            assert result.success is False
            assert "require Linux" in (result.error or "")

    def test_no_actions_is_noop(self, mock_linux_platform: Any, temp_home: Path) -> None:
        with patched_home_env(temp_home, clear=True):
            result = register_file_manager_actions([])
            assert result.success is True
            assert "No actions" in (result.message or "")

    def test_single_action_creates_files(self, mock_linux_platform: Any, temp_home: Path) -> None:
        with patched_home_env(temp_home, clear=True):
            action = DesktopAction("test-script", "Test Script", "python test.py")
            result = register_file_manager_actions([action], clean_existing=False)
            assert result.success is True
            assert "Registered 1 actions" in (result.message or "")

            actions_dir = get_actions_directory()
            scripts_dir = get_scripts_directory()

            desktop_file = actions_dir / "contextipy-test-script.desktop"
            script_file = scripts_dir / "contextipy-test-script.sh"

            assert desktop_file.exists()
            assert script_file.exists()

            desktop_content = desktop_file.read_text()
            assert "[Desktop Entry]" in desktop_content
            assert "Type=Action" in desktop_content
            assert "Name=Test Script" in desktop_content

            script_content = script_file.read_text()
            assert "#!/bin/bash" in script_content
            assert "python test.py" in script_content

            script_stat = script_file.stat()
            assert script_stat.st_mode & stat.S_IXUSR

    def test_action_with_icon(self, mock_linux_platform: Any, temp_home: Path) -> None:
        with patched_home_env(temp_home, clear=True):
            action = DesktopAction("test-script", "Test Script", "cmd", icon="icon.png")
            result = register_file_manager_actions([action], clean_existing=False)
            assert result.success is True

            actions_dir = get_actions_directory()
            desktop_file = actions_dir / "contextipy-test-script.desktop"
            desktop_content = desktop_file.read_text()
            assert "Icon=icon.png" in desktop_content

    def test_action_with_accepts_files(self, mock_linux_platform: Any, temp_home: Path) -> None:
        with patched_home_env(temp_home, clear=True):
            action = DesktopAction("test-script", "Test", "cmd", accepts=("file",))
            result = register_file_manager_actions([action], clean_existing=False)
            assert result.success is True

            actions_dir = get_actions_directory()
            desktop_file = actions_dir / "contextipy-test-script.desktop"
            desktop_content = desktop_file.read_text()
            assert "local-files" in desktop_content

    def test_action_with_accepts_directories(self, mock_linux_platform: Any, temp_home: Path) -> None:
        with patched_home_env(temp_home, clear=True):
            action = DesktopAction("test-script", "Test", "cmd", accepts=("directory",))
            result = register_file_manager_actions([action], clean_existing=False)
            assert result.success is True

            actions_dir = get_actions_directory()
            desktop_file = actions_dir / "contextipy-test-script.desktop"
            desktop_content = desktop_file.read_text()
            assert "directories" in desktop_content

    def test_multiple_actions(self, mock_linux_platform: Any, temp_home: Path) -> None:
        with patched_home_env(temp_home, clear=True):
            actions = [
                DesktopAction("script1", "Script 1", "cmd1"),
                DesktopAction("script2", "Script 2", "cmd2"),
            ]
            result = register_file_manager_actions(actions, clean_existing=False)
            assert result.success is True
            assert "Registered 2 actions" in (result.message or "")

            actions_dir = get_actions_directory()
            assert (actions_dir / "contextipy-script1.desktop").exists()
            assert (actions_dir / "contextipy-script2.desktop").exists()

    def test_clean_existing_removes_old_files(self, mock_linux_platform: Any, temp_home: Path) -> None:
        with patched_home_env(temp_home, clear=True):
            actions_dir = get_actions_directory()
            scripts_dir = get_scripts_directory()
            actions_dir.mkdir(parents=True, exist_ok=True)
            scripts_dir.mkdir(parents=True, exist_ok=True)

            old_desktop = actions_dir / "contextipy-old.desktop"
            old_script = scripts_dir / "contextipy-old.sh"
            old_desktop.write_text("old")
            old_script.write_text("old")

            action = DesktopAction("new", "New", "cmd")
            result = register_file_manager_actions([action], clean_existing=True)
            assert result.success is True

            assert not old_desktop.exists()
            assert not old_script.exists()
            assert (actions_dir / "contextipy-new.desktop").exists()


class TestUnregisterFileManagerActions:
    """Exercise menu removal."""

    def test_requires_linux(self) -> None:
        with patch("contextipy.os_integration.linux_integration.is_linux", return_value=False):
            result = unregister_file_manager_actions()
            assert result.success is False
            assert "require Linux" in (result.error or "")

    def test_no_files_present(self, mock_linux_platform: Any, temp_home: Path) -> None:
        with patched_home_env(temp_home, clear=True):
            result = unregister_file_manager_actions()
            assert result.success is True
            assert "No actions were present" in (result.message or "")

    def test_removes_existing_files(self, mock_linux_platform: Any, temp_home: Path) -> None:
        with patched_home_env(temp_home, clear=True):
            actions_dir = get_actions_directory()
            scripts_dir = get_scripts_directory()
            actions_dir.mkdir(parents=True, exist_ok=True)
            scripts_dir.mkdir(parents=True, exist_ok=True)

            desktop1 = actions_dir / "contextipy-test1.desktop"
            desktop2 = actions_dir / "contextipy-test2.desktop"
            script1 = scripts_dir / "contextipy-test1.sh"
            script2 = scripts_dir / "contextipy-test2.sh"

            desktop1.write_text("test")
            desktop2.write_text("test")
            script1.write_text("test")
            script2.write_text("test")

            result = unregister_file_manager_actions()
            assert result.success is True
            assert "Removed 2 actions" in (result.message or "")

            assert not desktop1.exists()
            assert not desktop2.exists()
            assert not script1.exists()
            assert not script2.exists()

    def test_does_not_remove_non_contextipy_files(
        self, mock_linux_platform: Any, temp_home: Path
    ) -> None:
        with patched_home_env(temp_home, clear=True):
            actions_dir = get_actions_directory()
            actions_dir.mkdir(parents=True, exist_ok=True)

            other_file = actions_dir / "other.desktop"
            other_file.write_text("test")

            result = unregister_file_manager_actions()
            assert result.success is True
            assert other_file.exists()


class TestUpdateOnScan:
    """Test integration with script scanning workflow."""

    def test_update_with_scripts(self, mock_linux_platform: Any, temp_home: Path) -> None:
        with patched_home_env(temp_home, clear=True):
            script = Mock()
            script.script_id = "script"
            script.module = "pkg"
            script.qualname = "pkg:func"
            script.title = "Title"
            script.group = ()
            script.icon = None
            script.accepts = ()

            result = update_file_manager_actions_on_scan([script])
            assert result.success is True

            actions_dir = get_actions_directory()
            assert (actions_dir / "contextipy-script.desktop").exists()

    def test_update_with_no_scripts_removes_all(
        self, mock_linux_platform: Any, temp_home: Path
    ) -> None:
        with patched_home_env(temp_home, clear=True):
            actions_dir = get_actions_directory()
            scripts_dir = get_scripts_directory()
            actions_dir.mkdir(parents=True, exist_ok=True)
            scripts_dir.mkdir(parents=True, exist_ok=True)

            desktop = actions_dir / "contextipy-old.desktop"
            script = scripts_dir / "contextipy-old.sh"
            desktop.write_text("test")
            script.write_text("test")

            result = update_file_manager_actions_on_scan([])
            assert result.success is True
            assert not desktop.exists()


class TestUpdateVisibility:
    """Test visibility filtering based on enabled state."""

    def test_update_visibility_with_enabled_filter(
        self, mock_linux_platform: Any, temp_home: Path
    ) -> None:
        with patched_home_env(temp_home, clear=True):
            script1 = Mock()
            script1.script_id = "script1"
            script1.module = "pkg"
            script1.qualname = "pkg:func1"
            script1.title = "Script 1"
            script1.group = ()
            script1.icon = None
            script1.accepts = ()

            script2 = Mock()
            script2.script_id = "script2"
            script2.module = "pkg"
            script2.qualname = "pkg:func2"
            script2.title = "Script 2"
            script2.group = ()
            script2.icon = None
            script2.accepts = ()

            result = update_file_manager_actions_visibility(
                [script1, script2],
                enabled_script_ids=["script1"],
            )
            assert result.success is True

            actions_dir = get_actions_directory()
            assert (actions_dir / "contextipy-script1.desktop").exists()
            assert not (actions_dir / "contextipy-script2.desktop").exists()

    def test_update_visibility_all_enabled(
        self, mock_linux_platform: Any, temp_home: Path
    ) -> None:
        with patched_home_env(temp_home, clear=True):
            script = Mock()
            script.script_id = "script"
            script.module = "pkg"
            script.qualname = "pkg:func"
            script.title = "Script"
            script.group = ()
            script.icon = None
            script.accepts = ()
            script.enabled = True

            result = update_file_manager_actions_visibility([script])
            assert result.success is True

            actions_dir = get_actions_directory()
            assert (actions_dir / "contextipy-script.desktop").exists()


class TestCleanupRemovedScripts:
    """Test cleanup after scripts are removed."""

    def test_cleanup_keeps_remaining_scripts(
        self, mock_linux_platform: Any, temp_home: Path
    ) -> None:
        with patched_home_env(temp_home, clear=True):
            actions_dir = get_actions_directory()
            scripts_dir = get_scripts_directory()
            actions_dir.mkdir(parents=True, exist_ok=True)
            scripts_dir.mkdir(parents=True, exist_ok=True)

            old_desktop = actions_dir / "contextipy-old.desktop"
            old_script = scripts_dir / "contextipy-old.sh"
            old_desktop.write_text("test")
            old_script.write_text("test")

            remaining_script = Mock()
            remaining_script.script_id = "remaining"
            remaining_script.module = "pkg"
            remaining_script.qualname = "pkg:func"
            remaining_script.title = "Remaining"
            remaining_script.group = ()
            remaining_script.icon = None
            remaining_script.accepts = ()

            result = cleanup_removed_scripts([remaining_script])
            assert result.success is True

            assert not old_desktop.exists()
            assert (actions_dir / "contextipy-remaining.desktop").exists()


class TestDesktopFileContent:
    """Verify desktop file content generation."""

    def test_desktop_file_has_required_sections(
        self, mock_linux_platform: Any, temp_home: Path
    ) -> None:
        with patched_home_env(temp_home, clear=True):
            action = DesktopAction("test", "Test", "cmd")
            result = register_file_manager_actions([action], clean_existing=False)
            assert result.success is True

            actions_dir = get_actions_directory()
            desktop_file = actions_dir / "contextipy-test.desktop"
            content = desktop_file.read_text()

            assert "[Desktop Entry]" in content
            assert "Type=Action" in content
            assert "Name=Test" in content
            assert "Profiles=" in content
            assert "[X-Action-Profile" in content
            assert "Exec=" in content
            assert "MimeTypes=" in content
            assert "SelectionCount=" in content

    def test_helper_script_has_shebang(self, mock_linux_platform: Any, temp_home: Path) -> None:
        with patched_home_env(temp_home, clear=True):
            action = DesktopAction("test", "Test", "python script.py")
            result = register_file_manager_actions([action], clean_existing=False)
            assert result.success is True

            scripts_dir = get_scripts_directory()
            script_file = scripts_dir / "contextipy-test.sh"
            content = script_file.read_text()

            lines = content.split("\n")
            assert lines[0] == "#!/bin/bash"
            assert "python script.py" in content
