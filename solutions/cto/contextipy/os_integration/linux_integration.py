"""Linux file manager integration via .desktop actions for Nautilus/Nemo.

This module is responsible for synchronising ContextiPY script metadata with
Linux file managers (Nautilus, Nemo, and compatible implementations) through
the desktop actions mechanism. Desktop action files are placed in
``~/.local/share/file-manager/actions`` following the freedesktop.org
specification. Each script is exposed as a standalone action that invokes
the ``contextipy.execution.context_entry`` module with the appropriate metadata.
Helper shell scripts are generated to bridge the desktop action system with
Python script execution, and permission bits are set appropriately.
"""

from __future__ import annotations

import logging
import os
import platform
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DesktopAction:
    """Description of a single file manager action to register."""

    script_id: str
    title: str
    command_line: str
    group: tuple[str, ...] = field(default_factory=tuple)
    icon: str | None = None
    accepts: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class RegistrationResult:
    """Outcome of a file manager integration operation."""

    success: bool
    message: str | None = None
    error: str | None = None


def is_linux() -> bool:
    """Return ``True`` when running on a Linux platform."""

    return sys.platform.startswith("linux") or platform.system() == "Linux"


def get_actions_directory() -> Path:
    """Return the directory where file manager actions should be placed."""

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        base = Path(xdg_data_home)
    else:
        base = Path.home() / ".local" / "share"
    return base / "file-manager" / "actions"


def get_scripts_directory() -> Path:
    """Return the directory where helper scripts should be placed."""

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        base = Path(xdg_data_home)
    else:
        base = Path.home() / ".local" / "share"
    return base / "contextipy" / "scripts"


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
        str(exe),
        "-m",
        "contextipy.execution.context_entry",
        f'"{target}"',
        '--files "$@"',
    ]
    return " ".join(parts)


def actions_from_scripts(
    scripts: Iterable[Any],
    *,
    python_executable: Path | None = None,
) -> list[DesktopAction]:
    """Convert script metadata objects into :class:`DesktopAction` instances.

    The *scripts* iterable can contain either objects that expose the metadata
    attributes directly (such as :class:`contextipy.scanner.script_scanner.ScannedScript`)
    or wrapper objects (such as :class:`contextipy.scanner.registry.RegisteredScript`).
    ``RegisteredScript`` instances expose a ``scanned`` attribute which holds the
    underlying ``ScannedScript``; this function automatically unwraps such
    objects. Duck typing is used to avoid importing the scanner modules here.
    """

    actions: list[DesktopAction] = []
    for script in scripts:
        source = getattr(script, "scanned", script)
        script_id = getattr(source, "script_id")
        module = getattr(source, "module")
        qualname = getattr(source, "qualname")
        title = getattr(source, "title")
        group_seq: Sequence[str] = tuple(getattr(source, "group", ()))
        icon = getattr(source, "icon", None)
        accepts_seq: Sequence[str] = tuple(getattr(source, "accepts", ()))

        command_line = build_command_line(module, qualname, script_id, python_executable)
        actions.append(
            DesktopAction(
                script_id=script_id,
                title=title,
                command_line=command_line,
                group=tuple(str(part) for part in group_seq),
                icon=icon if isinstance(icon, str) and icon else None,
                accepts=tuple(str(item) for item in accepts_seq),
            )
        )
    return actions


def _build_desktop_file_content(
    action: DesktopAction,
    helper_script_path: Path,
) -> str:
    """Build the content of a .desktop file for the given action."""

    lines = [
        "[Desktop Entry]",
        "Type=Action",
        f"Name={action.title}",
    ]

    if action.icon:
        lines.append(f"Icon={action.icon}")

    profile_parts = []
    if action.accepts:
        for accept_type in action.accepts:
            if accept_type.lower() in {"file", "files"}:
                profile_parts.append("local-files")
            elif accept_type.lower() in {"directory", "directories", "folder", "folders"}:
                profile_parts.append("directories")
    else:
        profile_parts.append("local-files")

    profiles = ";".join(profile_parts) + ";"
    lines.append(f"Profiles={profiles}")

    lines.append("")
    for idx, profile in enumerate(profile_parts):
        section_name = profile if idx == 0 else profile
        lines.append(f"[X-Action-Profile {section_name}]")
        lines.append(f"Exec={helper_script_path} %F")
        lines.append(f"MimeTypes=*/*;")
        if profile == "directories":
            lines.append("SelectionCount=>0")
        else:
            lines.append("SelectionCount=>0")
        lines.append("")

    return "\n".join(lines)


def _build_helper_script_content(command_line: str) -> str:
    """Build the content of a helper shell script."""

    lines = [
        "#!/bin/bash",
        "# Auto-generated helper script for ContextiPY",
        "",
        command_line,
    ]
    return "\n".join(lines)


def _sanitize_filename(name: str) -> str:
    """Return a filesystem-safe version of *name*."""

    cleaned = name.replace("/", "_").replace("\\", "_").replace(" ", "_")
    return "".join(char for char in cleaned if char.isalnum() or char in {"_", "-", "."})


def register_file_manager_actions(
    actions: Sequence[DesktopAction],
    *,
    clean_existing: bool = True,
) -> RegistrationResult:
    """Register *actions* as file manager context menu items."""

    if not is_linux():
        return RegistrationResult(False, error="File manager actions require Linux")

    if not actions:
        return RegistrationResult(True, message="No actions supplied for registration")

    actions_dir = get_actions_directory()
    scripts_dir = get_scripts_directory()

    try:
        actions_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.error("Failed to create directories: %s", exc)
        return RegistrationResult(False, error=f"Directory creation failed: {exc}")

    if clean_existing:
        result = unregister_file_manager_actions()
        if not result.success:
            logger.warning("Cleanup failed but continuing: %s", result.error)

    registered_count = 0
    for action in actions:
        try:
            desktop_filename = f"contextipy-{_sanitize_filename(action.script_id)}.desktop"
            script_filename = f"contextipy-{_sanitize_filename(action.script_id)}.sh"

            desktop_path = actions_dir / desktop_filename
            script_path = scripts_dir / script_filename

            script_content = _build_helper_script_content(action.command_line)
            script_path.write_text(script_content, encoding="utf-8")
            script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

            desktop_content = _build_desktop_file_content(action, script_path)
            desktop_path.write_text(desktop_content, encoding="utf-8")

            registered_count += 1
        except OSError as exc:
            logger.error("Failed to register action %s: %s", action.script_id, exc)
            return RegistrationResult(False, error=f"Registration failed for {action.script_id}: {exc}")

    return RegistrationResult(True, message=f"Registered {registered_count} actions")


def unregister_file_manager_actions() -> RegistrationResult:
    """Remove all ContextiPY file manager actions."""

    if not is_linux():
        return RegistrationResult(False, error="File manager actions require Linux")

    actions_dir = get_actions_directory()
    scripts_dir = get_scripts_directory()

    removed_count = 0

    if actions_dir.exists():
        try:
            for desktop_file in actions_dir.glob("contextipy-*.desktop"):
                desktop_file.unlink()
                removed_count += 1
        except OSError as exc:
            logger.error("Failed to remove desktop files: %s", exc)
            return RegistrationResult(False, error=f"Failed to remove desktop files: {exc}")

    if scripts_dir.exists():
        try:
            for script_file in scripts_dir.glob("contextipy-*.sh"):
                script_file.unlink()
        except OSError as exc:
            logger.error("Failed to remove helper scripts: %s", exc)
            return RegistrationResult(False, error=f"Failed to remove helper scripts: {exc}")

    if removed_count == 0:
        return RegistrationResult(True, message="No actions were present")
    return RegistrationResult(True, message=f"Removed {removed_count} actions")


def update_file_manager_actions_on_scan(
    scripts: Iterable[Any],
    *,
    python_executable: Path | None = None,
) -> RegistrationResult:
    """Refresh file manager actions after a scan discovers available scripts."""

    actions = actions_from_scripts(scripts, python_executable=python_executable)
    if actions:
        return register_file_manager_actions(actions, clean_existing=True)
    return unregister_file_manager_actions()


def update_file_manager_actions_visibility(
    scripts: Iterable[Any],
    *,
    python_executable: Path | None = None,
    enabled_script_ids: Sequence[str] | None = None,
) -> RegistrationResult:
    """Refresh file manager actions to reflect the current enabled script set."""

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

    return update_file_manager_actions_on_scan(
        filtered_scripts,
        python_executable=python_executable,
    )


def cleanup_removed_scripts(
    current_scripts: Iterable[Any],
    *,
    python_executable: Path | None = None,
) -> RegistrationResult:
    """Ensure file manager actions reflect the scripts that remain after removals."""

    return update_file_manager_actions_on_scan(
        current_scripts,
        python_executable=python_executable,
    )


__all__ = [
    "DesktopAction",
    "RegistrationResult",
    "is_linux",
    "get_actions_directory",
    "get_scripts_directory",
    "get_contextipy_executable",
    "build_command_line",
    "actions_from_scripts",
    "register_file_manager_actions",
    "unregister_file_manager_actions",
    "update_file_manager_actions_on_scan",
    "update_file_manager_actions_visibility",
    "cleanup_removed_scripts",
]
