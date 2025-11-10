"""Tests for Windows Registry integration module."""

from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from contextipy.os_integration.windows_registry import (
    MenuNode,
    RegistryCommand,
    RegistryResult,
    build_command_line,
    cleanup_removed_scripts,
    commands_from_scripts,
    get_contextipy_executable,
    get_windows_version,
    is_windows,
    register_shell_menu,
    supports_classic_context_menu,
    unregister_shell_menu,
    update_shell_menu_on_scan,
    update_shell_menu_visibility,
)


class MockWinregModule:
    """Lightweight winreg mock capturing registry writes for assertions."""

    HKEY_CURRENT_USER = "HKEY_CURRENT_USER"
    KEY_READ = 1
    KEY_WRITE = 2
    REG_SZ = 1

    def __init__(self) -> None:
        self.keys: dict[str, dict[str, Any]] = {}
        self.values: dict[str, dict[str, tuple[Any, int]]] = {}
        self._init_base_keys()

    def _init_base_keys(self) -> None:
        for target in (
            r"Software\Classes\*\shell",
            r"Software\Classes\Directory\shell",
            r"Software\Classes\Directory\Background\shell",
        ):
            full_path = f"{self.HKEY_CURRENT_USER}\\{target}"
            self.keys[full_path] = {}
            self.values[full_path] = {}

    def OpenKey(
        self,
        key: str | "MockRegistryKey",
        path: str,
        reserved: int,
        access: int,
    ) -> "MockRegistryKey":
        if isinstance(key, MockRegistryKey):
            full_path = f"{key.path}\\{path}"
        else:
            full_path = f"{key}\\{path}"
        if full_path not in self.keys:
            raise FileNotFoundError(full_path)
        return MockRegistryKey(self, full_path)

    def CreateKeyEx(
        self,
        parent: str | "MockRegistryKey",
        name: str,
        reserved: int,
        access: int,
    ) -> "MockRegistryKey":
        parent_path = parent.path if isinstance(parent, MockRegistryKey) else parent
        full_path = f"{parent_path}\\{name}"
        if full_path not in self.keys:
            self.keys[full_path] = {}
            self.values[full_path] = {}
        return MockRegistryKey(self, full_path)

    def SetValueEx(
        self,
        key: "MockRegistryKey",
        value_name: str,
        reserved: int,
        value_type: int,
        value: Any,
    ) -> None:
        self.values.setdefault(key.path, {})[value_name] = (value, value_type)

    def CloseKey(self, key: "MockRegistryKey") -> None:  # noqa: D401 - mock no-op
        return None

    def DeleteKey(self, parent_key: "MockRegistryKey", name: str) -> None:
        full_path = f"{parent_key.path}\\{name}"
        self.keys.pop(full_path, None)
        self.values.pop(full_path, None)

    def EnumKey(self, key: "MockRegistryKey", index: int) -> str:
        prefix = f"{key.path}\\"
        subkeys = sorted(
            k[len(prefix) :]
            for k in self.keys
            if k.startswith(prefix) and "\\" not in k[len(prefix) :]
        )
        if index >= len(subkeys):
            raise OSError("No more keys")
        return subkeys[index]


class MockRegistryKey:
    """Simple handle object returned by :class:`MockWinregModule`."""

    def __init__(self, winreg_module: MockWinregModule, path: str) -> None:
        self.winreg = winreg_module
        self.path = path

    def __enter__(self) -> "MockRegistryKey":
        return self

    def __exit__(self, *args: Any) -> None:
        return None


@pytest.fixture
def mock_winreg() -> MockWinregModule:
    """Provide a fresh mock winreg module for each test."""

    return MockWinregModule()


@pytest.fixture
def mock_windows_platform() -> Any:
    """Force the module to think it is running on Windows."""

    with patch("contextipy.os_integration.windows_registry.sys.platform", "win32"):
        with patch(
            "contextipy.os_integration.windows_registry.platform.system",
            return_value="Windows",
        ):
            yield


class TestPlatformDetection:
    """Ensure platform and version helpers behave as expected."""

    def test_is_windows_on_windows(self, mock_windows_platform: Any) -> None:
        assert is_windows() is True

    def test_is_windows_on_linux(self) -> None:
        with patch("contextipy.os_integration.windows_registry.sys.platform", "linux"):
            with patch(
                "contextipy.os_integration.windows_registry.platform.system",
                return_value="Linux",
            ):
                assert is_windows() is False

    def test_get_windows_version_on_windows(self, mock_windows_platform: Any) -> None:
        with patch(
            "contextipy.os_integration.windows_registry.platform.version",
            return_value="10.0.19041",
        ):
            assert get_windows_version() == (10, 0, 19041)

    def test_get_windows_version_short_format(self, mock_windows_platform: Any) -> None:
        with patch(
            "contextipy.os_integration.windows_registry.platform.version",
            return_value="10.0",
        ):
            assert get_windows_version() == (10, 0, 0)

    def test_get_windows_version_on_linux(self) -> None:
        with patch("contextipy.os_integration.windows_registry.sys.platform", "linux"):
            with patch(
                "contextipy.os_integration.windows_registry.platform.system",
                return_value="Linux",
            ):
                assert get_windows_version() is None

    def test_get_windows_version_invalid_format(self, mock_windows_platform: Any) -> None:
        with patch(
            "contextipy.os_integration.windows_registry.platform.version",
            return_value="invalid",
        ):
            assert get_windows_version() is None

    def test_supports_classic_context_menu_windows10(self, mock_windows_platform: Any) -> None:
        with patch(
            "contextipy.os_integration.windows_registry.platform.version",
            return_value="10.0.19041",
        ):
            assert supports_classic_context_menu() is True

    def test_supports_classic_context_menu_windows7(self, mock_windows_platform: Any) -> None:
        with patch(
            "contextipy.os_integration.windows_registry.platform.version",
            return_value="6.1.7601",
        ):
            assert supports_classic_context_menu() is True

    def test_supports_classic_context_menu_non_windows(self) -> None:
        with patch("contextipy.os_integration.windows_registry.sys.platform", "linux"):
            with patch(
                "contextipy.os_integration.windows_registry.platform.system",
                return_value="Linux",
            ):
                assert supports_classic_context_menu() is False


class TestCommandLineHelpers:
    """Validate command line helpers."""

    def test_build_command_line_custom_executable(self) -> None:
        python_exe = Path("/usr/bin/python3")
        command = build_command_line("pkg.module", "func", "script", python_exe)
        assert f'"{python_exe}"' in command
        assert "-m" in command
        assert "contextipy.execution.context_entry" in command
        assert '"pkg.module:func"' in command
        assert '--files "%V"' in command

    def test_build_command_line_defaults(self) -> None:
        command = build_command_line("pkg.module", "func", "script")
        assert "contextipy.execution.context_entry" in command

    def test_get_contextipy_executable(self) -> None:
        assert isinstance(get_contextipy_executable(), Path)


class TestDataclasses:
    """Basic smoke tests for data containers."""

    def test_registry_command_defaults(self) -> None:
        command = RegistryCommand("id", "Title", "python script.py")
        assert command.group == ()
        assert command.icon is None

    def test_registry_result_defaults(self) -> None:
        result = RegistryResult(True)
        assert result.success is True
        assert result.message is None
        assert result.error is None


class TestMenuNode:
    """Ensure tree structure creation works."""

    def test_add_command_without_group(self) -> None:
        node = MenuNode()
        command = RegistryCommand("id", "Title", "cmd")
        node.add_command(command)
        assert node.commands == [command]
        assert node.children == {}

    def test_add_command_with_single_group(self) -> None:
        node = MenuNode()
        command = RegistryCommand("id", "Title", "cmd", group=("Utilities",))
        node.add_command(command)
        assert not node.commands
        assert "Utilities" in node.children
        assert node.children["Utilities"].commands == [command]

    def test_add_command_with_nested_group(self) -> None:
        node = MenuNode()
        command = RegistryCommand("id", "Title", "cmd", group=("Utilities", "Images"))
        node.add_command(command)
        assert "Utilities" in node.children
        assert "Images" in node.children["Utilities"].children


class TestCommandsFromScripts:
    """Verify conversion from metadata objects."""

    def test_scanned_script(self) -> None:
        script = Mock()
        script.script_id = "script"
        script.module = "pkg"
        script.qualname = "pkg:func"
        script.title = "Title"
        script.group = ("Utilities",)
        script.icon = "icon.ico"

        commands = commands_from_scripts([script])
        assert len(commands) == 1
        assert commands[0].script_id == "script"
        assert commands[0].group == ("Utilities",)
        assert commands[0].icon == "icon.ico"

    def test_registered_script(self) -> None:
        scanned = Mock()
        scanned.script_id = "script"
        scanned.module = "pkg"
        scanned.qualname = "pkg:func"
        scanned.title = "Title"
        scanned.group = ()
        scanned.icon = None

        registered = Mock()
        registered.scanned = scanned

        commands = commands_from_scripts([registered])
        assert len(commands) == 1
        assert commands[0].script_id == "script"


class TestRegisterShellMenu:
    """Exercise the registration workflow."""

    def test_requires_windows(self) -> None:
        with patch("contextipy.os_integration.windows_registry.is_windows", return_value=False):
            result = register_shell_menu([RegistryCommand("id", "Title", "cmd")])
            assert result.success is False
            assert "require Windows" in (result.error or "")

    def test_requires_supported_version(self, mock_windows_platform: Any) -> None:
        with patch(
            "contextipy.os_integration.windows_registry.supports_classic_context_menu",
            return_value=False,
        ):
            result = register_shell_menu([RegistryCommand("id", "Title", "cmd")])
            assert result.success is False
            assert "not supported" in (result.error or "")

    def test_no_commands_is_noop(
        self, mock_windows_platform: Any, mock_winreg: MockWinregModule
    ) -> None:
        with patch(
            "contextipy.os_integration.windows_registry.supports_classic_context_menu",
            return_value=True,
        ), patch(
            "contextipy.os_integration.windows_registry._get_winreg",
            return_value=mock_winreg,
        ):
            result = register_shell_menu([])
            assert result.success is True
            assert "No commands" in (result.message or "")

    def test_single_command_registers_all_targets(
        self, mock_windows_platform: Any, mock_winreg: MockWinregModule
    ) -> None:
        with patch(
            "contextipy.os_integration.windows_registry.supports_classic_context_menu",
            return_value=True,
        ), patch(
            "contextipy.os_integration.windows_registry._get_winreg",
            return_value=mock_winreg,
        ):
            command = RegistryCommand("script", "Script", "python script.py", icon="icon.ico")
            result = register_shell_menu([command], submenu_name="ContextiPY")
            assert result.success is True
            assert "Registered 1 commands" in (result.message or "")

            submenu_path = (
                f"{mock_winreg.HKEY_CURRENT_USER}"
                r"\Software\Classes\Directory\Background\shell\ContextiPY"
            )
            assert submenu_path in mock_winreg.values
            assert mock_winreg.values[submenu_path]["MUIVerb"][0] == "ContextiPY"
            assert mock_winreg.values[submenu_path]["Icon"][0] == "icon.ico"

    def test_grouped_commands_create_hierarchy(
        self, mock_windows_platform: Any, mock_winreg: MockWinregModule
    ) -> None:
        with patch(
            "contextipy.os_integration.windows_registry.supports_classic_context_menu",
            return_value=True,
        ), patch(
            "contextipy.os_integration.windows_registry._get_winreg",
            return_value=mock_winreg,
        ):
            commands = [
                RegistryCommand(
                    "script1",
                    "Script 1",
                    "python script1.py",
                    group=("Utilities",),
                ),
                RegistryCommand(
                    "script2",
                    "Script 2",
                    "python script2.py",
                    group=("Utilities", "Images"),
                ),
            ]
            result = register_shell_menu(commands, submenu_name="ContextiPY")
            assert result.success is True

            utilities_key = (
                f"{mock_winreg.HKEY_CURRENT_USER}"
                r"\Software\Classes\Directory\Background\shell\ContextiPY\shell\group_0_Utilities"
            )
            assert utilities_key in mock_winreg.keys
            nested_key = utilities_key + r"\shell\group_0_Images"
            assert nested_key in mock_winreg.keys


class TestUnregisterShellMenu:
    """Exercise menu removal."""

    def test_requires_windows(self) -> None:
        with patch("contextipy.os_integration.windows_registry.is_windows", return_value=False):
            result = unregister_shell_menu()
            assert result.success is False

    def test_remove_existing(
        self, mock_windows_platform: Any, mock_winreg: MockWinregModule
    ) -> None:
        with patch(
            "contextipy.os_integration.windows_registry.supports_classic_context_menu",
            return_value=True,
        ), patch(
            "contextipy.os_integration.windows_registry._get_winreg",
            return_value=mock_winreg,
        ):
            register_shell_menu([RegistryCommand("id", "Title", "cmd")])
            result = unregister_shell_menu()
            assert result.success is True
            assert "Removed submenu" in (result.message or "")

    def test_remove_missing(
        self, mock_windows_platform: Any, mock_winreg: MockWinregModule
    ) -> None:
        with patch(
            "contextipy.os_integration.windows_registry._get_winreg",
            return_value=mock_winreg,
        ):
            result = unregister_shell_menu(submenu_name="Missing")
            assert result.success is True
            assert "not present" in (result.message or "")


class TestUpdateFunctions:
    """Verify higher-level update helpers."""

    def _make_script(self, script_id: str, *, enabled: bool = True) -> Mock:
        script = Mock()
        script.script_id = script_id
        script.module = "pkg"
        script.qualname = "pkg:func"
        script.title = script_id.title()
        script.group = ()
        script.icon = None
        script.enabled = enabled
        return script

    def test_update_on_scan_registers_commands(
        self, mock_windows_platform: Any, mock_winreg: MockWinregModule
    ) -> None:
        scripts = [self._make_script("script1"), self._make_script("script2")]
        with patch(
            "contextipy.os_integration.windows_registry.supports_classic_context_menu",
            return_value=True,
        ), patch(
            "contextipy.os_integration.windows_registry._get_winreg",
            return_value=mock_winreg,
        ):
            result = update_shell_menu_on_scan(scripts, submenu_name="ContextiPY")
            assert result.success is True
            assert "Registered 2 commands" in (result.message or "")

    def test_update_on_scan_no_scripts_removes(
        self, mock_windows_platform: Any, mock_winreg: MockWinregModule
    ) -> None:
        with patch(
            "contextipy.os_integration.windows_registry._get_winreg",
            return_value=mock_winreg,
        ):
            result = update_shell_menu_on_scan([], submenu_name="ContextiPY")
            assert result.success is True

    def test_update_visibility_with_enabled_ids(
        self, mock_windows_platform: Any, mock_winreg: MockWinregModule
    ) -> None:
        scripts = [self._make_script("script1"), self._make_script("script2")]
        with patch(
            "contextipy.os_integration.windows_registry.supports_classic_context_menu",
            return_value=True,
        ), patch(
            "contextipy.os_integration.windows_registry._get_winreg",
            return_value=mock_winreg,
        ):
            result = update_shell_menu_visibility(
                scripts,
                submenu_name="ContextiPY",
                enabled_script_ids=["script1"],
            )
            assert result.success is True

    def test_update_visibility_uses_enabled_property_when_missing_ids(
        self, mock_windows_platform: Any, mock_winreg: MockWinregModule
    ) -> None:
        scripts = [self._make_script("script1", enabled=True), self._make_script("script2", enabled=False)]
        with patch(
            "contextipy.os_integration.windows_registry.supports_classic_context_menu",
            return_value=True,
        ), patch(
            "contextipy.os_integration.windows_registry._get_winreg",
            return_value=mock_winreg,
        ):
            result = update_shell_menu_visibility(scripts, submenu_name="ContextiPY")
            assert result.success is True

    def test_cleanup_removed_scripts(
        self, mock_windows_platform: Any, mock_winreg: MockWinregModule
    ) -> None:
        scripts = [self._make_script("script1")]
        with patch(
            "contextipy.os_integration.windows_registry.supports_classic_context_menu",
            return_value=True,
        ), patch(
            "contextipy.os_integration.windows_registry._get_winreg",
            return_value=mock_winreg,
        ):
            result = cleanup_removed_scripts(scripts, submenu_name="ContextiPY")
            assert result.success is True


class TestHelperFunctions:
    """Cover internal helpers surfaced for testing."""

    def test_sanitize_key_name(self) -> None:
        from contextipy.os_integration.windows_registry import _sanitize_key_name

        assert _sanitize_key_name("simple") == "simple"
        assert _sanitize_key_name("with:colon") == "with_colon"
        assert _sanitize_key_name("with/slash") == "with_slash"
        assert _sanitize_key_name("with\\backslash") == "with_backslash"

    def test_select_icon(self) -> None:
        from contextipy.os_integration.windows_registry import _select_icon

        commands = [
            RegistryCommand("script1", "Title", "cmd"),
            RegistryCommand("script2", "Title", "cmd", icon="icon.ico"),
        ]
        assert _select_icon(commands) == "icon.ico"
        assert _select_icon([RegistryCommand("script", "Title", "cmd")]) is None


class TestIntegrationLifecycle:
    """Exercise a representative end-to-end flow."""

    def test_full_cycle(
        self, mock_windows_platform: Any, mock_winreg: MockWinregModule
    ) -> None:
        with patch(
            "contextipy.os_integration.windows_registry.supports_classic_context_menu",
            return_value=True,
        ), patch(
            "contextipy.os_integration.windows_registry._get_winreg",
            return_value=mock_winreg,
        ):
            commands = [
                RegistryCommand("script1", "Script 1", "python script1.py"),
                RegistryCommand("script2", "Script 2", "python script2.py", icon="icon.ico"),
            ]
            assert register_shell_menu(commands, submenu_name="TestMenu").success is True
            assert unregister_shell_menu(submenu_name="TestMenu").success is True

    def test_scan_then_toggle_visibility(
        self, mock_windows_platform: Any, mock_winreg: MockWinregModule
    ) -> None:
        scripts = [
            TestUpdateFunctions()._make_script("script1"),
            TestUpdateFunctions()._make_script("script2"),
            TestUpdateFunctions()._make_script("script3"),
        ]
        with patch(
            "contextipy.os_integration.windows_registry.supports_classic_context_menu",
            return_value=True,
        ), patch(
            "contextipy.os_integration.windows_registry._get_winreg",
            return_value=mock_winreg,
        ):
            assert update_shell_menu_on_scan(scripts).success is True
            assert (
                update_shell_menu_visibility(
                    scripts, enabled_script_ids=["script1", "script3"]
                ).success
                is True
            )
