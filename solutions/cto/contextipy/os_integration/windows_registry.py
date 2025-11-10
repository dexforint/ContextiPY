"""Windows Registry integration for ContextiPY shell context menu entries.

This module is responsible for synchronising ContextiPY script metadata with the
classic Windows (Windows 10 style) context menu that appears when right-clicking
files, folders, or background space. The implementation targets keys under
``HKEY_CURRENT_USER`` so that registration does not require elevation and the
changes apply per-user. A single ``ContextiPY`` submenu is created which can
contain nested groupings that mirror the script grouping metadata discovered by
the scanner. Each script is exposed as an individual command that invokes the
``contextipy.execution.context_entry`` module with the appropriate metadata.
"""

from __future__ import annotations

import logging
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

logger = logging.getLogger(__name__)

# Registry locations used to surface items in the classic Windows context menu.
_CLASSIC_CONTEXT_TARGETS: tuple[str, ...] = (
    r"Software\Classes\*\shell",
    r"Software\Classes\Directory\shell",
    r"Software\Classes\Directory\Background\shell",
)


@dataclass(frozen=True, slots=True)
class RegistryCommand:
    """Description of a single context menu command to register."""

    script_id: str
    title: str
    command_line: str
    group: tuple[str, ...] = field(default_factory=tuple)
    icon: str | None = None


@dataclass(frozen=True, slots=True)
class RegistryResult:
    """Outcome of a registry manipulation operation."""

    success: bool
    message: str | None = None
    error: str | None = None


class MenuNode:
    """Tree node representing grouped menu structure for registration."""

    __slots__ = ("commands", "children")

    def __init__(self) -> None:
        self.commands: list[RegistryCommand] = []
        self.children: dict[str, "MenuNode"] = {}

    def add_command(self, command: RegistryCommand) -> None:
        node = self
        for part in command.group:
            node = node.children.setdefault(part, MenuNode())
        node.commands.append(command)


def is_windows() -> bool:
    """Return ``True`` when running on a Windows platform."""

    return sys.platform == "win32" or platform.system() == "Windows"


def get_windows_version() -> tuple[int, int, int] | None:
    """Return the Windows version as ``(major, minor, build)`` when available."""

    if not is_windows():
        return None

    try:
        version_str = platform.version()
        parts = version_str.split(".")
    except Exception:  # pragma: no cover - defensive fallback
        return None

    try:
        if len(parts) >= 3:
            return int(parts[0]), int(parts[1]), int(parts[2])
        if len(parts) == 2:
            return int(parts[0]), int(parts[1]), 0
        return int(parts[0]), 0, 0
    except (ValueError, IndexError):
        return None


def supports_classic_context_menu() -> bool:
    """Return ``True`` if the detected Windows version supports the classic menu."""

    version = get_windows_version()
    if version is None:
        return False

    major, minor, _build = version
    if major >= 10:
        return True
    if major == 6 and minor >= 1:  # Windows 7 / 8.x / 8.1
        return True
    return False


def _get_winreg() -> Any:
    """Import and return the ``winreg`` module, raising if unavailable."""

    if not is_windows():
        raise RuntimeError("winreg is only available on Windows platforms")

    try:  # pragma: no cover - executed only on Windows
        import winreg  # type: ignore
    except ImportError as exc:  # pragma: no cover - executed only on Windows
        raise RuntimeError("winreg module could not be imported") from exc
    return winreg


def get_contextipy_executable() -> Path:
    """Return the Python executable responsible for running ContextiPY."""

    return Path(sys.executable)


def build_command_line(
    module: str,
    qualname: str,
    script_id: str,
    python_executable: Path | None = None,
) -> str:
    """Build the command line used to invoke ``context_entry`` for *script_id*."""

    exe = python_executable or get_contextipy_executable()
    target = f"{module}:{qualname}"
    parts = [
        f'"{exe}"',
        "-m",
        "contextipy.execution.context_entry",
        f'"{target}"',
        '--files "%V"',
    ]
    return " ".join(parts)


def commands_from_scripts(
    scripts: Iterable[Any],
    *,
    python_executable: Path | None = None,
) -> list[RegistryCommand]:
    """Convert script metadata objects into :class:`RegistryCommand` instances.

    The *scripts* iterable can contain either objects that expose the metadata
    attributes directly (such as :class:`contextipy.scanner.script_scanner.ScannedScript`)
    or wrapper objects (such as :class:`contextipy.scanner.registry.RegisteredScript`).
    ``RegisteredScript`` instances expose a ``scanned`` attribute which holds the
    underlying ``ScannedScript``; this function automatically unwraps such
    objects. Duck typing is used to avoid importing the scanner modules here.
    """

    commands: list[RegistryCommand] = []
    for script in scripts:
        source = getattr(script, "scanned", script)
        script_id = getattr(source, "script_id")
        module = getattr(source, "module")
        qualname = getattr(source, "qualname")
        title = getattr(source, "title")
        group_seq: Sequence[str] = tuple(getattr(source, "group", ()))
        icon = getattr(source, "icon", None)

        command_line = build_command_line(module, qualname, script_id, python_executable)
        commands.append(
            RegistryCommand(
                script_id=script_id,
                title=title,
                command_line=command_line,
                group=tuple(str(part) for part in group_seq),
                icon=icon if isinstance(icon, str) and icon else None,
            )
        )
    return commands


def register_shell_menu(
    commands: Sequence[RegistryCommand],
    *,
    submenu_name: str = "ContextiPY",
) -> RegistryResult:
    """Register *commands* in the Windows classic context menu."""

    if not is_windows():
        return RegistryResult(False, error="Registry operations require Windows")
    if not supports_classic_context_menu():
        return RegistryResult(False, error="Classic Windows context menu not supported")

    if not commands:
        return RegistryResult(True, message="No commands supplied for registration")

    try:
        winreg = _get_winreg()
    except RuntimeError as exc:
        return RegistryResult(False, error=str(exc))

    try:
        for base_path in _CLASSIC_CONTEXT_TARGETS:
            _register_under_path(winreg, base_path, submenu_name, commands)
    except Exception as exc:  # pragma: no cover - requires Windows for real errors
        logger.error("Failed to register context menu: %s", exc)
        return RegistryResult(False, error=f"Registry operation failed: {exc}")

    return RegistryResult(True, message=f"Registered {len(commands)} commands")


def unregister_shell_menu(*, submenu_name: str = "ContextiPY") -> RegistryResult:
    """Remove the ContextiPY submenu from the Windows classic context menu."""

    if not is_windows():
        return RegistryResult(False, error="Registry operations require Windows")

    try:
        winreg = _get_winreg()
    except RuntimeError as exc:
        return RegistryResult(False, error=str(exc))

    try:
        removed_any = False
        for base_path in _CLASSIC_CONTEXT_TARGETS:
            removed = _delete_submenu_if_present(winreg, base_path, submenu_name)
            removed_any = removed_any or removed
        if removed_any:
            return RegistryResult(True, message=f"Removed submenu '{submenu_name}'")
        return RegistryResult(True, message=f"Submenu '{submenu_name}' not present")
    except Exception as exc:  # pragma: no cover - requires Windows for real errors
        logger.error("Failed to unregister context menu: %s", exc)
        return RegistryResult(False, error=f"Registry operation failed: {exc}")


def update_shell_menu_on_scan(
    scripts: Iterable[Any],
    *,
    submenu_name: str = "ContextiPY",
    python_executable: Path | None = None,
) -> RegistryResult:
    """Refresh registry entries after a scan discovers available scripts."""

    commands = commands_from_scripts(scripts, python_executable=python_executable)
    if commands:
        unregister_shell_menu(submenu_name=submenu_name)
        return register_shell_menu(commands, submenu_name=submenu_name)
    return unregister_shell_menu(submenu_name=submenu_name)


def update_shell_menu_visibility(
    scripts: Iterable[Any],
    *,
    submenu_name: str = "ContextiPY",
    python_executable: Path | None = None,
    enabled_script_ids: Sequence[str] | None = None,
) -> RegistryResult:
    """Refresh registry entries to reflect the current enabled script set."""

    enabled_lookup = set(enabled_script_ids or [])

    filtered_scripts: list[Any] = []
    for script in scripts:
        script_id = getattr(script, "script_id", None)
        if script_id is None:
            source = getattr(script, "scanned", script)
            script_id = getattr(source, "script_id", None)
        if script_id is None:
            continue

        if enabled_script_ids is None:
            enabled = getattr(script, "enabled", True)
        else:
            enabled = script_id in enabled_lookup
        if enabled:
            filtered_scripts.append(script)

    return update_shell_menu_on_scan(
        filtered_scripts,
        submenu_name=submenu_name,
        python_executable=python_executable,
    )


def cleanup_removed_scripts(
    current_scripts: Iterable[Any],
    *,
    submenu_name: str = "ContextiPY",
    python_executable: Path | None = None,
) -> RegistryResult:
    """Ensure the registry reflects the scripts that remain after removals."""

    return update_shell_menu_on_scan(
        current_scripts,
        submenu_name=submenu_name,
        python_executable=python_executable,
    )


def _register_under_path(
    winreg: Any,
    base_path: str,
    submenu_name: str,
    commands: Sequence[RegistryCommand],
) -> None:
    """Create or update the ContextiPY submenu under *base_path*."""

    base_key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, base_path, 0, winreg.KEY_WRITE)
    submenu_key = winreg.CreateKeyEx(base_key, submenu_name, 0, winreg.KEY_WRITE)
    winreg.SetValueEx(submenu_key, "MUIVerb", 0, winreg.REG_SZ, submenu_name)
    winreg.SetValueEx(submenu_key, "SubCommands", 0, winreg.REG_SZ, "")

    icon = _select_icon(commands)
    if icon:
        winreg.SetValueEx(submenu_key, "Icon", 0, winreg.REG_SZ, icon)

    shell_key = winreg.CreateKeyEx(submenu_key, "shell", 0, winreg.KEY_WRITE)

    tree = MenuNode()
    for command in commands:
        tree.add_command(command)

    _write_menu_tree(winreg, shell_key, tree)

    winreg.CloseKey(shell_key)
    winreg.CloseKey(submenu_key)
    winreg.CloseKey(base_key)


def _delete_submenu_if_present(winreg: Any, base_path: str, submenu_name: str) -> bool:
    """Delete the submenu named *submenu_name* if it exists."""

    try:
        base_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, base_path, 0, winreg.KEY_WRITE)
    except FileNotFoundError:
        return False

    try:
        _delete_key_recursive(winreg, base_key, submenu_name)
    except FileNotFoundError:
        winreg.CloseKey(base_key)
        return False

    winreg.CloseKey(base_key)
    return True


def _write_menu_tree(winreg: Any, parent_shell_key: Any, node: MenuNode) -> None:
    """Write *node* into the registry under *parent_shell_key*."""

    for index, command in enumerate(node.commands):
        key_name = f"cmd_{index}_{_sanitize_key_name(command.script_id)}"
        command_key = winreg.CreateKeyEx(parent_shell_key, key_name, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(command_key, "MUIVerb", 0, winreg.REG_SZ, command.title)
        if command.icon:
            winreg.SetValueEx(command_key, "Icon", 0, winreg.REG_SZ, command.icon)
        command_subkey = winreg.CreateKeyEx(command_key, "command", 0, winreg.KEY_WRITE)
        winreg.SetValueEx(command_subkey, "", 0, winreg.REG_SZ, command.command_line)
        winreg.CloseKey(command_subkey)
        winreg.CloseKey(command_key)

    for index, (group_name, child) in enumerate(node.children.items()):
        key_name = f"group_{index}_{_sanitize_key_name(group_name)}"
        group_key = winreg.CreateKeyEx(parent_shell_key, key_name, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(group_key, "MUIVerb", 0, winreg.REG_SZ, group_name)
        group_icon = _select_icon(child.commands)
        if group_icon:
            winreg.SetValueEx(group_key, "Icon", 0, winreg.REG_SZ, group_icon)
        child_shell_key = winreg.CreateKeyEx(group_key, "shell", 0, winreg.KEY_WRITE)
        _write_menu_tree(winreg, child_shell_key, child)
        winreg.CloseKey(child_shell_key)
        winreg.CloseKey(group_key)


def _select_icon(commands: Sequence[RegistryCommand]) -> str | None:
    """Return the first icon defined within *commands*, if any."""

    for command in commands:
        if command.icon:
            return command.icon
    return None


def _sanitize_key_name(name: str) -> str:
    """Return a registry-safe version of *name*."""

    cleaned = name.replace("\\", "_").replace("/", "_").replace(":", "_")
    return "".join(char for char in cleaned if char.isalnum() or char in {"_", "-"})


def _delete_key_recursive(winreg: Any, parent_key: Any, name: str) -> None:
    """Recursively delete *name* and all of its subkeys from *parent_key*."""

    key = winreg.OpenKey(parent_key, name, 0, winreg.KEY_READ | winreg.KEY_WRITE)
    index = 0
    while True:
        try:
            subkey_name = winreg.EnumKey(key, index)
        except OSError:
            break
        _delete_key_recursive(winreg, key, subkey_name)
        index += 1
    winreg.CloseKey(key)
    winreg.DeleteKey(parent_key, name)


__all__ = [
    "RegistryCommand",
    "RegistryResult",
    "commands_from_scripts",
    "cleanup_removed_scripts",
    "build_command_line",
    "get_contextipy_executable",
    "get_windows_version",
    "is_windows",
    "register_shell_menu",
    "supports_classic_context_menu",
    "unregister_shell_menu",
    "update_shell_menu_on_scan",
    "update_shell_menu_visibility",
]
