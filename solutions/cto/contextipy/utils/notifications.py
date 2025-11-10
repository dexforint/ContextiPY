"""Native toast notifications with platform-specific implementations.

This module provides cross-platform notification support with graceful fallbacks:
- Windows: win10toast or pywin32 balloons
- Linux: libnotify via notify2
- Fallback: system tray popups via PySide6

The NotificationCenter class provides both synchronous and queued notification
delivery, with Settings integration for user-controlled suppression.
"""

from __future__ import annotations

import platform
import queue
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol

from contextipy.config.settings import Settings


@dataclass(frozen=True, slots=True)
class NotificationResult:
    """Result of attempting to show a notification."""

    success: bool
    message: str | None = None


class NotificationProvider(ABC):
    """Abstract base for platform-specific notification providers."""

    @abstractmethod
    def show(self, title: str, message: str | None = None, **kwargs: Any) -> NotificationResult:
        """Display a notification with the given title and optional message."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available on the current system."""
        ...


class WindowsNotificationProvider(NotificationProvider):
    """Windows notification provider using win10toast or pywin32."""

    def __init__(self) -> None:
        self._toaster: Any = None
        self._use_win10toast = False
        self._use_pywin32 = False
        self._init_provider()

    def _init_provider(self) -> None:
        """Initialize the best available Windows notification provider."""
        try:
            from win10toast import ToastNotifier

            self._toaster = ToastNotifier()
            self._use_win10toast = True
        except ImportError:
            try:
                import win32gui

                self._use_pywin32 = True
            except ImportError:
                pass

    def is_available(self) -> bool:
        """Check if Windows notifications are available."""
        return self._use_win10toast or self._use_pywin32

    def show(self, title: str, message: str | None = None, **kwargs: Any) -> NotificationResult:
        """Display a Windows notification."""
        if self._use_win10toast:
            return self._show_win10toast(title, message, **kwargs)
        if self._use_pywin32:
            return self._show_pywin32(title, message)
        return NotificationResult(
            success=False, message="No Windows notification provider available"
        )

    def _show_win10toast(
        self, title: str, message: str | None = None, **kwargs: Any
    ) -> NotificationResult:
        """Show notification using win10toast."""
        try:
            msg = message or ""
            duration = kwargs.get("duration", 5)
            threaded = kwargs.get("threaded", True)
            self._toaster.show_toast(
                title,
                msg,
                duration=duration,
                threaded=threaded,
            )
            return NotificationResult(success=True, message="Notification shown via win10toast")
        except Exception as exc:
            return NotificationResult(success=False, message=f"win10toast error: {exc}")

    def _show_pywin32(self, title: str, message: str | None = None) -> NotificationResult:
        """Show notification using pywin32 balloon tips."""
        try:
            import win32api
            import win32con
            import win32gui

            msg = message or ""

            class_name = "ContextipyNotification"
            wc = win32gui.WNDCLASS()
            hinst = wc.hInstance = win32api.GetModuleHandle(None)
            wc.lpszClassName = class_name
            wc.lpfnWndProc = {}

            try:
                class_atom = win32gui.RegisterClass(wc)
            except Exception:
                class_atom = win32gui.WNDCLASS(win32gui.GetClassInfo(hinst, class_name)).lpszClassName  # type: ignore[assignment]

            hwnd = win32gui.CreateWindow(
                class_atom,
                "Taskbar",
                0,
                0,
                0,
                win32con.CW_USEDEFAULT,
                win32con.CW_USEDEFAULT,
                0,
                0,
                hinst,
                None,
            )
            win32gui.UpdateWindow(hwnd)

            flags = win32gui.NIF_INFO | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
            nid = (hwnd, 0, flags, win32con.WM_USER + 20, 0, "Tooltip")

            win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
            win32gui.Shell_NotifyIcon(
                win32gui.NIM_MODIFY,
                (hwnd, 0, win32gui.NIF_INFO, win32con.WM_USER + 20, 0, "Balloon Tooltip", msg, 200, title),  # type: ignore[arg-type]
            )

            threading.Timer(5.0, lambda: win32gui.DestroyWindow(hwnd)).start()

            return NotificationResult(success=True, message="Notification shown via pywin32")
        except Exception as exc:
            return NotificationResult(success=False, message=f"pywin32 error: {exc}")


class LinuxNotificationProvider(NotificationProvider):
    """Linux notification provider using libnotify via notify2."""

    def __init__(self) -> None:
        self._notify: Any = None
        self._init_provider()

    def _init_provider(self) -> None:
        """Initialize notify2 for Linux notifications."""
        try:
            import notify2

            notify2.init("Contextipy")
            self._notify = notify2
        except ImportError:
            pass
        except Exception:
            pass

    def is_available(self) -> bool:
        """Check if notify2 is available."""
        return self._notify is not None

    def show(self, title: str, message: str | None = None, **kwargs: Any) -> NotificationResult:
        """Display a Linux notification."""
        if not self._notify:
            return NotificationResult(
                success=False, message="notify2 not available (install python3-notify2)"
            )

        try:
            msg = message or ""
            notification = self._notify.Notification(title, msg)
            notification.show()
            return NotificationResult(success=True, message="Notification shown via notify2")
        except Exception as exc:
            return NotificationResult(success=False, message=f"notify2 error: {exc}")


class TrayNotificationProvider(NotificationProvider):
    """Fallback notification provider using PySide6 system tray."""

    def __init__(self, tray_icon: Any = None) -> None:
        """Initialize with an optional QSystemTrayIcon instance.

        Args:
            tray_icon: A QSystemTrayIcon instance. If None, this provider
                       will not be available until set_tray_icon() is called.
        """
        self._tray_icon = tray_icon

    def set_tray_icon(self, tray_icon: Any) -> None:
        """Set the tray icon for notifications."""
        self._tray_icon = tray_icon

    def is_available(self) -> bool:
        """Check if tray icon is available."""
        if self._tray_icon is None:
            return False
        try:
            return self._tray_icon.supportsMessages()
        except Exception:
            return False

    def show(self, title: str, message: str | None = None, **kwargs: Any) -> NotificationResult:
        """Display a tray popup notification."""
        if not self._tray_icon:
            return NotificationResult(success=False, message="No tray icon available")

        try:
            from PySide6.QtWidgets import QSystemTrayIcon

            msg = message or ""
            duration = kwargs.get("duration", 5) * 1000
            icon_type = kwargs.get("icon_type", QSystemTrayIcon.MessageIcon.Information)

            self._tray_icon.showMessage(title, msg, icon_type, duration)
            return NotificationResult(success=True, message="Notification shown via tray")
        except Exception as exc:
            return NotificationResult(success=False, message=f"Tray notification error: {exc}")


class StubNotificationProvider(NotificationProvider):
    """Stub provider for testing or unsupported platforms."""

    def is_available(self) -> bool:
        """Stub provider is always available."""
        return True

    def show(self, title: str, message: str | None = None, **kwargs: Any) -> NotificationResult:
        """Stub notification that succeeds without side effects."""
        return NotificationResult(success=True, message="Notification delivered (stub)")


class SettingsProvider(Protocol):
    """Protocol for settings access."""

    def load(self) -> Settings:
        """Load current settings."""
        ...


class NotificationCenter:
    """Central notification manager with queue support and settings integration.

    This class provides the main API for showing notifications in Contextipy.
    It automatically selects the best available provider for the platform,
    respects user suppression preferences, and supports both synchronous
    and queued notification delivery.
    """

    def __init__(
        self,
        *,
        settings_provider: SettingsProvider | None = None,
        tray_icon: Any = None,
        provider: NotificationProvider | None = None,
    ) -> None:
        """Initialize the notification center.

        Args:
            settings_provider: Optional settings provider for suppression checks.
            tray_icon: Optional QSystemTrayIcon for tray fallback.
            provider: Optional provider override (mainly for testing).
        """
        self._settings_provider = settings_provider
        self._provider = provider or self._select_provider(tray_icon)
        self._queue: queue.Queue[tuple[str, str | None, dict[str, Any]]] = queue.Queue()
        self._worker_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def _select_provider(self, tray_icon: Any = None) -> NotificationProvider:
        """Select the best available notification provider for the platform."""
        system = platform.system()

        if system == "Windows":
            provider = WindowsNotificationProvider()
            if provider.is_available():
                return provider

        elif system == "Linux":
            provider = LinuxNotificationProvider()
            if provider.is_available():
                return provider

        tray_provider = TrayNotificationProvider(tray_icon)
        if tray_provider.is_available():
            return tray_provider

        return StubNotificationProvider()

    def set_tray_icon(self, tray_icon: Any) -> None:
        """Update the tray icon for fallback notifications.

        If the current provider is a TrayNotificationProvider, this updates
        its tray icon. If using a stub provider, this may switch to tray.
        """
        if isinstance(self._provider, TrayNotificationProvider):
            self._provider.set_tray_icon(tray_icon)
        elif isinstance(self._provider, StubNotificationProvider):
            tray_provider = TrayNotificationProvider(tray_icon)
            if tray_provider.is_available():
                self._provider = tray_provider

    def _is_suppressed(self) -> bool:
        """Check if notifications are suppressed by settings."""
        if self._settings_provider is None:
            return False
        try:
            settings = self._settings_provider.load()
            return not settings.enable_notifications
        except Exception:
            return False

    def show_notification(
        self, title: str, message: str | None = None, **kwargs: Any
    ) -> NotificationResult:
        """Show a notification synchronously.

        Args:
            title: Notification title.
            message: Optional notification body.
            **kwargs: Additional provider-specific options.

        Returns:
            NotificationResult indicating success or failure.
        """
        if not title:
            return NotificationResult(success=False, message="Notification title is required")

        if self._is_suppressed():
            return NotificationResult(success=True, message="Notifications suppressed by settings")

        return self._provider.show(title, message, **kwargs)

    def queue_notification(self, title: str, message: str | None = None, **kwargs: Any) -> None:
        """Queue a notification for asynchronous delivery.

        Args:
            title: Notification title.
            message: Optional notification body.
            **kwargs: Additional provider-specific options.
        """
        if not title:
            return

        self._queue.put((title, message, kwargs))

        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._start_worker()

    def _start_worker(self) -> None:
        """Start the background worker thread for processing queued notifications."""
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()

    def _process_queue(self) -> None:
        """Process queued notifications in the background."""
        while not self._stop_event.is_set():
            try:
                title, message, kwargs = self._queue.get(timeout=1.0)
                self.show_notification(title, message, **kwargs)
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception:
                continue

    def stop(self) -> None:
        """Stop the background worker thread and clear the queue."""
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)

        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                break

    def notify_error(self, error: str, context: str | None = None) -> NotificationResult:
        """Show an error notification.

        This is a convenience method for error reporting throughout the application.

        Args:
            error: The error message to display.
            context: Optional context or location where the error occurred.

        Returns:
            NotificationResult indicating success or failure.
        """
        title = "Error"
        if context:
            title = f"Error: {context}"
        return self.show_notification(title, error)

    def notify_repeat(
        self, title: str, message: str | None = None, count: int = 1
    ) -> NotificationResult:
        """Show a notification with repeat count information.

        This is useful for log aggregation where multiple similar events occur.

        Args:
            title: Notification title.
            message: Optional notification body.
            count: Number of times the event occurred.

        Returns:
            NotificationResult indicating success or failure.
        """
        if count > 1:
            repeat_suffix = f" ({count}x)"
            title = title + repeat_suffix

        return self.show_notification(title, message)


def get_notification_center(
    settings_provider: SettingsProvider | None = None,
    tray_icon: Any = None,
) -> NotificationCenter:
    """Factory function to create a NotificationCenter instance.

    Args:
        settings_provider: Optional settings provider for suppression checks.
        tray_icon: Optional QSystemTrayIcon for tray fallback.

    Returns:
        A configured NotificationCenter instance.
    """
    return NotificationCenter(settings_provider=settings_provider, tray_icon=tray_icon)


__all__ = [
    "NotificationCenter",
    "NotificationProvider",
    "NotificationResult",
    "WindowsNotificationProvider",
    "LinuxNotificationProvider",
    "TrayNotificationProvider",
    "StubNotificationProvider",
    "get_notification_center",
]
