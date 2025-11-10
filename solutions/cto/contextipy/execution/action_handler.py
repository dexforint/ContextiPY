"""Action handler for executing Contextipy actions cross-platform.

This module provides the core infrastructure for dispatching actions to the
underlying operating system. It abstracts platform-specific operations behind
clean interfaces, ensuring that higher layers do not need to know about Windows,
macOS, or Linux specifics. Error handling is graceful and results are returned
as ``ActionResult`` instances rather than raising exceptions.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from contextipy.actions import (
    Action,
    Copy,
    Folder,
    Link,
    NoneAction,
    Notify,
    Open,
    Text,
    serialize_action_for_log,
)
from contextipy.config.settings import SettingsStore
from contextipy.utils.notifications import NotificationCenter, get_notification_center


@dataclass(frozen=True, slots=True)
class ActionResult:
    """Result of attempting to execute an action."""

    success: bool
    message: str | None = None


class ClipboardInterface(Protocol):
    """Protocol for cross-platform clipboard operations."""

    def copy_text(self, text: str) -> ActionResult:
        """Copy the given text to the system clipboard."""
        ...


class NotificationInterface(Protocol):
    """Protocol for cross-platform notifications."""

    def show_notification(self, title: str, message: str | None = None) -> ActionResult:
        """Display a user notification."""
        ...


class FileOpenerInterface(Protocol):
    """Protocol for opening files or folders with the system handler."""

    def open_path(self, path: Path) -> ActionResult:
        """Open *path* using the system default application."""
        ...


class WindowsClipboard:
    """Windows implementation of clipboard operations."""

    def copy_text(self, text: str) -> ActionResult:
        try:
            import win32clipboard

            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text)
            win32clipboard.CloseClipboard()
            return ActionResult(success=True, message="Text copied to clipboard")
        except ImportError:
            return ActionResult(
                success=False,
                message="win32clipboard not available; install pywin32",
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            return ActionResult(success=False, message=f"Clipboard operation failed: {exc}")


class MacOSClipboard:
    """macOS implementation of clipboard operations."""

    def copy_text(self, text: str) -> ActionResult:
        try:
            subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True, capture_output=True)
            return ActionResult(success=True, message="Text copied to clipboard")
        except subprocess.CalledProcessError as exc:
            return ActionResult(success=False, message=f"pbcopy failed: {exc}")
        except FileNotFoundError:
            return ActionResult(success=False, message="pbcopy not available on this system")
        except Exception as exc:  # pragma: no cover - defensive fallback
            return ActionResult(success=False, message=f"Clipboard operation failed: {exc}")


class LinuxClipboard:
    """Linux implementation of clipboard operations."""

    def copy_text(self, text: str) -> ActionResult:
        for command in ("xclip", "xsel"):
            if shutil.which(command) is None:
                continue

            try:
                if command == "xclip":
                    subprocess.run(
                        [command, "-selection", "clipboard"],
                        input=text.encode("utf-8"),
                        check=True,
                        capture_output=True,
                    )
                else:
                    subprocess.run(
                        [command, "--clipboard", "--input"],
                        input=text.encode("utf-8"),
                        check=True,
                        capture_output=True,
                    )
                return ActionResult(success=True, message="Text copied to clipboard")
            except subprocess.CalledProcessError as exc:
                return ActionResult(success=False, message=f"{command} failed: {exc}")
            except Exception as exc:  # pragma: no cover - defensive fallback
                return ActionResult(success=False, message=f"Clipboard operation failed: {exc}")

        return ActionResult(
            success=False,
            message="No clipboard command found (install xclip or xsel)",
        )


class NotificationCenterAdapter:
    """Adapter to use NotificationCenter with ActionHandler's NotificationInterface."""

    def __init__(self, notification_center: NotificationCenter | None = None) -> None:
        """Initialize with an optional NotificationCenter instance.

        Args:
            notification_center: NotificationCenter instance. If None, creates a new one.
        """
        self._center = notification_center or get_notification_center()

    def show_notification(self, title: str, message: str | None = None) -> ActionResult:
        """Show a notification using the NotificationCenter."""
        result = self._center.show_notification(title, message)
        return ActionResult(success=result.success, message=result.message)



class UniversalFileOpener:
    """Universal file opener using platform-appropriate commands."""

    def open_path(self, path: Path) -> ActionResult:
        if not path.exists():
            return ActionResult(success=False, message=f"Path does not exist: {path}")

        try:
            system = platform.system()
            if system == "Windows":
                subprocess.run(["start", "", str(path)], shell=True, check=True)
            elif system == "Darwin":
                subprocess.run(["open", str(path)], check=True)
            elif system == "Linux":
                subprocess.run(["xdg-open", str(path)], check=True)
            else:
                return ActionResult(success=False, message=f"Unsupported platform: {system}")
            return ActionResult(success=True, message=f"Opened {path}")
        except subprocess.CalledProcessError as exc:
            return ActionResult(success=False, message=f"Failed to open path: {exc}")
        except FileNotFoundError:
            return ActionResult(success=False, message="File opener command not available")
        except Exception as exc:  # pragma: no cover - defensive fallback
            return ActionResult(success=False, message=f"Open operation failed: {exc}")


def _get_clipboard_impl() -> ClipboardInterface:
    """Return the clipboard implementation for the current platform."""

    system = platform.system()
    if system == "Windows":
        return WindowsClipboard()
    if system == "Darwin":
        return MacOSClipboard()
    return LinuxClipboard()


def _get_notification_impl() -> NotificationInterface:
    """Return the notification implementation for the current platform."""

    settings_store = SettingsStore()
    center = get_notification_center(settings_provider=settings_store)
    return NotificationCenterAdapter(center)


def _get_file_opener_impl() -> FileOpenerInterface:
    """Return the file opener implementation for the current platform."""

    return UniversalFileOpener()


class ActionHandler:
    """Dispatcher responsible for executing actions with graceful error handling."""

    def __init__(
        self,
        *,
        clipboard: ClipboardInterface | None = None,
        notification: NotificationInterface | None = None,
        file_opener: FileOpenerInterface | None = None,
        dry_run: bool = False,
    ) -> None:
        """Initialise the action handler.

        Parameters
        ----------
        clipboard:
            Optional clipboard implementation (useful for testing).
        notification:
            Optional notification implementation (useful for testing).
        file_opener:
            Optional file opener implementation (useful for testing).
        dry_run:
            When ``True``, actions are validated but not executed.
        """

        self._clipboard = clipboard or _get_clipboard_impl()
        self._notification = notification or _get_notification_impl()
        self._file_opener = file_opener or _get_file_opener_impl()
        self._dry_run = dry_run

    def execute(self, action: Action) -> ActionResult:
        """Execute *action* and return the result."""

        try:
            if isinstance(action, Open):
                return self._execute_open(action)
            if isinstance(action, Folder):
                return self._execute_folder(action)
            if isinstance(action, Link):
                return self._execute_link(action)
            if isinstance(action, Copy):
                return self._execute_copy(action)
            if isinstance(action, Notify):
                return self._execute_notify(action)
            if isinstance(action, Text):
                return self._execute_text(action)
            if isinstance(action, NoneAction):
                return self._execute_none(action)
        except Exception as exc:  # pragma: no cover - defensive fallback
            serialised = serialize_action_for_log(action)
            return ActionResult(success=False, message=f"Unexpected error {serialised}: {exc}")

        return ActionResult(success=False, message=f"Unknown action type: {type(action)!r}")

    def _execute_open(self, action: Open) -> ActionResult:
        path = action.target
        if not path.exists():
            return ActionResult(success=False, message=f"Target does not exist: {path}")
        if self._dry_run:
            return ActionResult(success=True, message=f"Dry-run: would open {path}")
        return self._file_opener.open_path(path)

    def _execute_folder(self, action: Folder) -> ActionResult:
        path = action.target
        if not path.exists():
            return ActionResult(success=False, message=f"Folder does not exist: {path}")
        if not path.is_dir():
            return ActionResult(success=False, message=f"Target is not a folder: {path}")
        if self._dry_run:
            return ActionResult(success=True, message=f"Dry-run: would open folder {path}")
        return self._file_opener.open_path(path)

    def _execute_link(self, action: Link) -> ActionResult:
        if self._dry_run:
            return ActionResult(success=True, message=f"Dry-run: would open URL {action.url}")
        try:
            webbrowser.open(action.url)
            return ActionResult(success=True, message=f"Opened URL: {action.url}")
        except Exception as exc:
            return ActionResult(success=False, message=f"Failed to open URL: {exc}")

    def _execute_copy(self, action: Copy) -> ActionResult:
        if not action.text:
            return ActionResult(success=False, message="Cannot copy empty text")
        if self._dry_run:
            return ActionResult(success=True, message="Dry-run: would copy text to clipboard")
        return self._clipboard.copy_text(action.text)

    def _execute_notify(self, action: Notify) -> ActionResult:
        if not action.title:
            return ActionResult(success=False, message="Notification title is required")
        if self._dry_run:
            return ActionResult(success=True, message="Dry-run: would show notification")
        return self._notification.show_notification(action.title, action.message)

    def _execute_text(self, action: Text) -> ActionResult:
        if self._dry_run:
            return ActionResult(success=True, message="Dry-run: would output text")
        try:
            sys.stdout.write(action.content)
            sys.stdout.write("\n")
            sys.stdout.flush()
            return ActionResult(success=True, message="Text written to stdout")
        except Exception as exc:
            return ActionResult(success=False, message=f"Failed to write text: {exc}")

    def _execute_none(self, action: NoneAction) -> ActionResult:
        reason = action.reason or "No action specified"
        if self._dry_run:
            return ActionResult(success=True, message=f"Dry-run: {reason}")
        return ActionResult(success=True, message=reason)


__all__ = [
    "ActionHandler",
    "ActionResult",
    "ClipboardInterface",
    "NotificationInterface",
    "FileOpenerInterface",
    "NotificationCenterAdapter",
]
