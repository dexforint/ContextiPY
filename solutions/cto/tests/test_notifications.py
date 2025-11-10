"""Tests for the notification system with platform mocks."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock, patch

import pytest

from contextipy.config.settings import Settings
from contextipy.utils.notifications import (
    LinuxNotificationProvider,
    NotificationCenter,
    NotificationResult,
    StubNotificationProvider,
    TrayNotificationProvider,
    WindowsNotificationProvider,
    get_notification_center,
)


class MockSettingsProvider:
    """Mock settings provider for testing."""

    def __init__(self, enable_notifications: bool = True) -> None:
        self.enable_notifications = enable_notifications

    def load(self) -> Settings:
        return Settings(enable_notifications=self.enable_notifications)


class TestWindowsNotificationProvider:
    """Tests for Windows notification provider."""

    def test_win10toast_available(self) -> None:
        """Test initialization with win10toast available."""
        with patch("contextipy.utils.notifications.platform.system", return_value="Windows"):
            mock_toaster = Mock()
            with patch.dict("sys.modules", {"win10toast": Mock(ToastNotifier=Mock(return_value=mock_toaster))}):
                provider = WindowsNotificationProvider()
                assert provider.is_available()

    def test_win10toast_show(self) -> None:
        """Test showing notification with win10toast."""
        mock_toaster = Mock()
        mock_module = Mock(ToastNotifier=Mock(return_value=mock_toaster))

        with patch.dict("sys.modules", {"win10toast": mock_module}):
            provider = WindowsNotificationProvider()
            result = provider.show("Test Title", "Test Message")

            assert result.success
            mock_toaster.show_toast.assert_called_once()
            call_args = mock_toaster.show_toast.call_args
            assert call_args[0][0] == "Test Title"
            assert call_args[0][1] == "Test Message"

    def test_win10toast_error(self) -> None:
        """Test handling errors from win10toast."""
        mock_toaster = Mock()
        mock_toaster.show_toast.side_effect = Exception("Toast error")
        mock_module = Mock(ToastNotifier=Mock(return_value=mock_toaster))

        with patch.dict("sys.modules", {"win10toast": mock_module}):
            provider = WindowsNotificationProvider()
            result = provider.show("Test", "Message")

            assert not result.success
            assert "error" in result.message.lower()

    def test_pywin32_fallback(self) -> None:
        """Test fallback to pywin32 when win10toast unavailable."""
        with patch.dict("sys.modules", {"win10toast": None}):
            with patch("contextipy.utils.notifications.WindowsNotificationProvider._init_provider") as mock_init:
                provider = WindowsNotificationProvider()
                provider._use_pywin32 = True
                assert provider.is_available()

    def test_no_provider_available(self) -> None:
        """Test when no Windows notification provider is available."""
        provider = WindowsNotificationProvider()
        provider._use_win10toast = False
        provider._use_pywin32 = False

        result = provider.show("Test", "Message")
        assert not result.success
        assert "not available" in result.message.lower()


class TestLinuxNotificationProvider:
    """Tests for Linux notification provider."""

    def test_notify2_available(self) -> None:
        """Test initialization with notify2 available."""
        mock_notify2 = Mock()
        mock_notify2.init = Mock()

        with patch.dict("sys.modules", {"notify2": mock_notify2}):
            provider = LinuxNotificationProvider()
            assert provider.is_available()
            mock_notify2.init.assert_called_once_with("Contextipy")

    def test_notify2_show(self) -> None:
        """Test showing notification with notify2."""
        mock_notification = Mock()
        mock_notify2 = Mock()
        mock_notify2.init = Mock()
        mock_notify2.Notification = Mock(return_value=mock_notification)

        with patch.dict("sys.modules", {"notify2": mock_notify2}):
            provider = LinuxNotificationProvider()
            result = provider.show("Test Title", "Test Message")

            assert result.success
            mock_notify2.Notification.assert_called_once_with("Test Title", "Test Message")
            mock_notification.show.assert_called_once()

    def test_notify2_unavailable(self) -> None:
        """Test when notify2 is not available."""
        with patch.dict("sys.modules", {"notify2": None}):
            provider = LinuxNotificationProvider()
            assert not provider.is_available()

            result = provider.show("Test", "Message")
            assert not result.success
            assert "not available" in result.message.lower()

    def test_notify2_error(self) -> None:
        """Test handling errors from notify2."""
        mock_notify2 = Mock()
        mock_notify2.init = Mock()
        mock_notify2.Notification.side_effect = Exception("Notify error")

        with patch.dict("sys.modules", {"notify2": mock_notify2}):
            provider = LinuxNotificationProvider()
            result = provider.show("Test", "Message")

            assert not result.success
            assert "error" in result.message.lower()


class TestTrayNotificationProvider:
    """Tests for tray notification provider."""

    def test_no_tray_icon(self) -> None:
        """Test provider without tray icon."""
        provider = TrayNotificationProvider()
        assert not provider.is_available()

    def test_with_tray_icon(self) -> None:
        """Test provider with tray icon."""
        mock_tray = Mock()
        mock_tray.supportsMessages = Mock(return_value=True)

        provider = TrayNotificationProvider(mock_tray)
        assert provider.is_available()

    def test_show_with_tray(self) -> None:
        """Test showing notification via tray."""
        mock_tray = Mock()
        mock_tray.supportsMessages = Mock(return_value=True)
        mock_tray.showMessage = Mock()

        provider = TrayNotificationProvider(mock_tray)
        result = provider.show("Test Title", "Test Message")

        assert result.success
        mock_tray.showMessage.assert_called_once()

    def test_show_without_tray(self) -> None:
        """Test showing notification without tray icon."""
        provider = TrayNotificationProvider()
        result = provider.show("Test", "Message")

        assert not result.success
        assert "no tray icon" in result.message.lower()

    def test_set_tray_icon(self) -> None:
        """Test setting tray icon after initialization."""
        provider = TrayNotificationProvider()
        assert not provider.is_available()

        mock_tray = Mock()
        mock_tray.supportsMessages = Mock(return_value=True)
        provider.set_tray_icon(mock_tray)

        assert provider.is_available()


class TestStubNotificationProvider:
    """Tests for stub notification provider."""

    def test_always_available(self) -> None:
        """Test stub provider is always available."""
        provider = StubNotificationProvider()
        assert provider.is_available()

    def test_show_succeeds(self) -> None:
        """Test stub provider always succeeds."""
        provider = StubNotificationProvider()
        result = provider.show("Test", "Message")

        assert result.success
        assert "stub" in result.message.lower()


class TestNotificationCenterProviderSelection:
    """Tests for provider selection logic."""

    @patch("contextipy.utils.notifications.platform.system")
    def test_windows_provider_selected(self, mock_system: Any) -> None:
        """Test Windows provider is selected on Windows."""
        mock_system.return_value = "Windows"

        with patch.object(WindowsNotificationProvider, "is_available", return_value=True):
            center = NotificationCenter()
            assert isinstance(center._provider, WindowsNotificationProvider)

    @patch("contextipy.utils.notifications.platform.system")
    def test_linux_provider_selected(self, mock_system: Any) -> None:
        """Test Linux provider is selected on Linux."""
        mock_system.return_value = "Linux"

        with patch.object(LinuxNotificationProvider, "is_available", return_value=True):
            center = NotificationCenter()
            assert isinstance(center._provider, LinuxNotificationProvider)

    @patch("contextipy.utils.notifications.platform.system")
    def test_tray_fallback(self, mock_system: Any) -> None:
        """Test fallback to tray when platform provider unavailable."""
        mock_system.return_value = "Windows"

        mock_tray = Mock()
        mock_tray.supportsMessages = Mock(return_value=True)

        with patch.object(WindowsNotificationProvider, "is_available", return_value=False):
            center = NotificationCenter(tray_icon=mock_tray)
            assert isinstance(center._provider, TrayNotificationProvider)

    @patch("contextipy.utils.notifications.platform.system")
    def test_stub_fallback(self, mock_system: Any) -> None:
        """Test fallback to stub when no providers available."""
        mock_system.return_value = "Darwin"

        center = NotificationCenter()
        assert isinstance(center._provider, StubNotificationProvider)

    def test_provider_override(self) -> None:
        """Test overriding provider for testing."""
        custom_provider = StubNotificationProvider()
        center = NotificationCenter(provider=custom_provider)
        assert center._provider is custom_provider


class TestNotificationCenterSuppression:
    """Tests for notification suppression via settings."""

    def test_notifications_enabled(self) -> None:
        """Test notifications shown when enabled in settings."""
        settings_provider = MockSettingsProvider(enable_notifications=True)
        provider = StubNotificationProvider()

        center = NotificationCenter(
            settings_provider=settings_provider,
            provider=provider,
        )

        result = center.show_notification("Test", "Message")
        assert result.success

    def test_notifications_disabled(self) -> None:
        """Test notifications suppressed when disabled in settings."""
        settings_provider = MockSettingsProvider(enable_notifications=False)
        provider = StubNotificationProvider()

        center = NotificationCenter(
            settings_provider=settings_provider,
            provider=provider,
        )

        result = center.show_notification("Test", "Message")
        assert result.success
        assert "suppressed" in result.message.lower()

    def test_no_settings_provider(self) -> None:
        """Test notifications work without settings provider."""
        provider = StubNotificationProvider()
        center = NotificationCenter(provider=provider)

        result = center.show_notification("Test", "Message")
        assert result.success


class TestNotificationCenterSynchronous:
    """Tests for synchronous notification delivery."""

    def test_show_notification_success(self) -> None:
        """Test successful synchronous notification."""
        provider = StubNotificationProvider()
        center = NotificationCenter(provider=provider)

        result = center.show_notification("Title", "Message")
        assert result.success

    def test_show_notification_empty_title(self) -> None:
        """Test notification fails with empty title."""
        provider = StubNotificationProvider()
        center = NotificationCenter(provider=provider)

        result = center.show_notification("", "Message")
        assert not result.success
        assert "required" in result.message.lower()

    def test_show_notification_no_message(self) -> None:
        """Test notification works with title only."""
        provider = StubNotificationProvider()
        center = NotificationCenter(provider=provider)

        result = center.show_notification("Title")
        assert result.success


class TestNotificationCenterQueued:
    """Tests for queued notification delivery."""

    def test_queue_notification(self) -> None:
        """Test queuing a notification."""
        provider = StubNotificationProvider()
        center = NotificationCenter(provider=provider)

        center.queue_notification("Title", "Message")
        assert not center._queue.empty()
        center.stop()

    def test_queue_empty_title(self) -> None:
        """Test queuing with empty title is ignored."""
        provider = StubNotificationProvider()
        center = NotificationCenter(provider=provider)

        center.queue_notification("", "Message")
        assert center._queue.empty()

    def test_worker_thread_started(self) -> None:
        """Test worker thread starts when queue is not empty."""
        provider = StubNotificationProvider()
        center = NotificationCenter(provider=provider)

        center.queue_notification("Title", "Message")
        assert center._worker_thread is not None
        center.stop()

    def test_stop_clears_queue(self) -> None:
        """Test stop clears the queue."""
        provider = StubNotificationProvider()
        center = NotificationCenter(provider=provider)

        center.queue_notification("Title1", "Message1")
        center.queue_notification("Title2", "Message2")
        center.stop()

        assert center._queue.empty()


class TestNotificationCenterErrorReporting:
    """Tests for error notification convenience method."""

    def test_notify_error_without_context(self) -> None:
        """Test error notification without context."""
        provider = StubNotificationProvider()
        center = NotificationCenter(provider=provider)

        result = center.notify_error("Something went wrong")
        assert result.success

    def test_notify_error_with_context(self) -> None:
        """Test error notification with context."""
        provider = StubNotificationProvider()
        center = NotificationCenter(provider=provider)

        result = center.notify_error("File not found", context="File Operations")
        assert result.success


class TestNotificationCenterRepeat:
    """Tests for repeat notification functionality."""

    def test_notify_repeat_single(self) -> None:
        """Test repeat notification with count of 1."""
        provider = StubNotificationProvider()
        center = NotificationCenter(provider=provider)

        result = center.notify_repeat("Event occurred", "Details", count=1)
        assert result.success

    def test_notify_repeat_multiple(self) -> None:
        """Test repeat notification with count > 1."""
        provider = StubNotificationProvider()
        center = NotificationCenter(provider=provider)

        result = center.notify_repeat("Event occurred", "Details", count=5)
        assert result.success


class TestNotificationCenterTrayIntegration:
    """Tests for tray icon integration."""

    def test_set_tray_icon_on_tray_provider(self) -> None:
        """Test setting tray icon when using tray provider."""
        mock_tray1 = Mock()
        mock_tray1.supportsMessages = Mock(return_value=True)

        center = NotificationCenter(tray_icon=mock_tray1)

        if isinstance(center._provider, TrayNotificationProvider):
            mock_tray2 = Mock()
            mock_tray2.supportsMessages = Mock(return_value=True)
            center.set_tray_icon(mock_tray2)

            assert center._provider._tray_icon is mock_tray2

    def test_set_tray_icon_upgrades_stub(self) -> None:
        """Test setting tray icon upgrades stub provider."""
        center = NotificationCenter(provider=StubNotificationProvider())

        mock_tray = Mock()
        mock_tray.supportsMessages = Mock(return_value=True)
        center.set_tray_icon(mock_tray)

        assert isinstance(center._provider, TrayNotificationProvider)


class TestGetNotificationCenter:
    """Tests for the factory function."""

    def test_factory_creates_center(self) -> None:
        """Test factory function creates a NotificationCenter."""
        center = get_notification_center()
        assert isinstance(center, NotificationCenter)

    def test_factory_with_settings(self) -> None:
        """Test factory function with settings provider."""
        settings_provider = MockSettingsProvider()
        center = get_notification_center(settings_provider=settings_provider)
        assert center._settings_provider is settings_provider

    def test_factory_with_tray(self) -> None:
        """Test factory function with tray icon."""
        mock_tray = Mock()
        mock_tray.supportsMessages = Mock(return_value=True)
        center = get_notification_center(tray_icon=mock_tray)
        assert isinstance(center, NotificationCenter)
