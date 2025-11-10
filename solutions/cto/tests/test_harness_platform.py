"""Tests demonstrating platform mocking for cross-platform code."""

from __future__ import annotations

import sys

import pytest


class TestPlatformDetection:
    """Test platform-specific detection using platform mocks."""

    def test_windows_detection(self, mock_platform_windows) -> None:
        """Test Windows platform detection."""
        import platform

        assert platform.system() == "Windows"
        assert sys.platform == "win32"

    def test_linux_detection(self, mock_platform_linux) -> None:
        """Test Linux platform detection."""
        import platform

        assert platform.system() == "Linux"
        assert sys.platform == "linux"

    def test_macos_detection(self, mock_platform_macos) -> None:
        """Test macOS platform detection."""
        import platform

        assert platform.system() == "Darwin"
        assert sys.platform == "darwin"


class TestPlatformSpecificCode:
    """Test platform-specific code paths."""

    def test_windows_specific_function(self, mock_platform_windows) -> None:
        """Test function that only runs on Windows."""
        import platform

        def get_platform_name() -> str:
            if platform.system() == "Windows":
                return "Windows Platform"
            return "Other Platform"

        assert get_platform_name() == "Windows Platform"

    def test_linux_specific_function(self, mock_platform_linux) -> None:
        """Test function that only runs on Linux."""
        import platform

        def get_platform_name() -> str:
            if platform.system() == "Linux":
                return "Linux Platform"
            return "Other Platform"

        assert get_platform_name() == "Linux Platform"


@pytest.mark.windows_only
class TestWindowsOnly:
    """Tests that only run on Windows."""

    def test_windows_feature(self) -> None:
        """Test a Windows-specific feature."""
        assert sys.platform == "win32"


@pytest.mark.linux_only
class TestLinuxOnly:
    """Tests that only run on Linux."""

    def test_linux_feature(self) -> None:
        """Test a Linux-specific feature."""
        assert sys.platform == "linux"


@pytest.mark.macos_only
class TestMacOSOnly:
    """Tests that only run on macOS."""

    def test_macos_feature(self) -> None:
        """Test a macOS-specific feature."""
        assert sys.platform == "darwin"
