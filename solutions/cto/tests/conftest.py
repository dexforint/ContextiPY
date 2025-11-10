"""Shared pytest fixtures and configuration for contextipy tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock, Mock, patch

import pytest


@pytest.fixture
def temp_script_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for script files.
    
    This fixture provides an isolated directory for testing script
    discovery, scanning, and execution without affecting the system.
    
    Returns:
        Path to the temporary script directory
    """
    script_dir = tmp_path / "scripts"
    script_dir.mkdir(parents=True, exist_ok=True)
    return script_dir


@pytest.fixture
def mock_platform_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock platform.system() to simulate Windows environment.
    
    Use this fixture when testing Windows-specific code paths.
    
    Args:
        monkeypatch: pytest's monkeypatch fixture
    """
    import platform
    
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(platform, "release", lambda: "10")
    monkeypatch.setattr(sys, "platform", "win32")


@pytest.fixture
def mock_platform_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock platform.system() to simulate Linux environment.
    
    Use this fixture when testing Linux-specific code paths.
    
    Args:
        monkeypatch: pytest's monkeypatch fixture
    """
    import platform
    
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(platform, "release", lambda: "5.10.0")
    monkeypatch.setattr(sys, "platform", "linux")


@pytest.fixture
def mock_platform_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock platform.system() to simulate macOS environment.
    
    Use this fixture when testing macOS-specific code paths.
    
    Args:
        monkeypatch: pytest's monkeypatch fixture
    """
    import platform
    
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(platform, "release", lambda: "21.0.0")
    monkeypatch.setattr(sys, "platform", "darwin")


@pytest.fixture
def mock_subprocess() -> Generator[MagicMock, None, None]:
    """Mock subprocess.run to isolate subprocess execution.
    
    This fixture prevents actual subprocess execution during tests,
    allowing for controlled testing of subprocess-dependent code.
    
    Yields:
        Mock subprocess.run function with configurable return values
    
    Example:
        def test_script_execution(mock_subprocess):
            mock_subprocess.return_value = Mock(
                returncode=0,
                stdout=b"output",
                stderr=b""
            )
            # test code here
    """
    with patch("subprocess.run") as mock:
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.stdout = b""
        mock_process.stderr = b""
        mock.return_value = mock_process
        yield mock


@pytest.fixture
def mock_subprocess_popen() -> Generator[MagicMock, None, None]:
    """Mock subprocess.Popen to isolate long-running subprocess execution.
    
    This fixture prevents actual subprocess creation during tests,
    useful for testing service/daemon management.
    
    Yields:
        Mock subprocess.Popen class with configurable behavior
    """
    with patch("subprocess.Popen") as mock:
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Process still running
        mock_process.returncode = None
        mock_process.communicate.return_value = (b"", b"")
        mock_process.wait.return_value = 0
        mock.return_value = mock_process
        yield mock


@pytest.fixture
def isolated_registry() -> Generator[None, None, None]:
    """Isolate the global script registry to prevent test interference.
    
    Clears the registry before and after each test to ensure tests
    don't affect each other through shared global state.
    
    Yields:
        None
    """
    from contextipy.core import decorators
    
    original_id_registry = dict(decorators._ID_REGISTRY)
    original_service_targets = dict(decorators._SERVICE_TARGETS)
    original_service_metadata = dict(decorators._SERVICE_METADATA)
    
    decorators._ID_REGISTRY.clear()
    decorators._SERVICE_TARGETS.clear()
    decorators._SERVICE_METADATA.clear()
    
    try:
        yield
    finally:
        decorators._ID_REGISTRY.clear()
        decorators._SERVICE_TARGETS.clear()
        decorators._SERVICE_METADATA.clear()
        decorators._ID_REGISTRY.update(original_id_registry)
        decorators._SERVICE_TARGETS.update(original_service_targets)
        decorators._SERVICE_METADATA.update(original_service_metadata)


@pytest.fixture
def sample_script_file(temp_script_dir: Path) -> Path:
    """Create a sample script file for testing.
    
    Generates a basic Python script with contextipy decorators
    that can be used for testing script discovery and execution.
    
    Args:
        temp_script_dir: Temporary directory fixture
    
    Returns:
        Path to the created script file
    """
    script_path = temp_script_dir / "sample_script.py"
    script_content = '''"""Sample test script."""

from contextipy import oneshot_script
from contextipy.actions import Text

@oneshot_script(
    script_id="sample_script",
    title="Sample Script",
    description="A sample script for testing",
)
def sample() -> Text:
    """Execute the sample script."""
    return Text("Hello from sample script")
'''
    script_path.write_text(script_content, encoding="utf-8")
    return script_path


@pytest.fixture
def sample_service_file(temp_script_dir: Path) -> Path:
    """Create a sample service file for testing.
    
    Generates a Python script with service and service_script decorators
    for testing service management functionality.
    
    Args:
        temp_script_dir: Temporary directory fixture
    
    Returns:
        Path to the created service file
    """
    service_path = temp_script_dir / "sample_service.py"
    service_content = '''"""Sample test service."""

import time
from contextipy import service, service_script

@service(
    service_id="sample_service",
    title="Sample Service",
    description="A sample service for testing",
)
def sample_service() -> None:
    """Run the sample service."""
    while True:
        time.sleep(1)

@service_script(
    script_id="stop_service",
    service_id="sample_service",
    title="Stop Service",
    description="Stop the sample service",
)
def stop_service() -> None:
    """Stop the service."""
    pass
'''
    service_path.write_text(service_content, encoding="utf-8")
    return service_path


@pytest.fixture
def mock_home_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Mock the user's home directory for config/data storage tests.
    
    Redirects HOME/USERPROFILE environment variables to a temporary
    directory to isolate file system operations.
    
    Args:
        tmp_path: pytest's temporary path fixture
        monkeypatch: pytest's monkeypatch fixture
    
    Returns:
        Path to the mocked home directory
    """
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    
    # Also mock Path.home() if needed
    if hasattr(Path, "home"):
        monkeypatch.setattr(Path, "home", lambda: home)
    
    return home


@pytest.fixture
def disable_qt() -> Generator[None, None, None]:
    """Disable Qt/GUI operations for headless testing.
    
    Ensures tests can run in headless environments (CI) without
    requiring X11/display server.
    
    Yields:
        None
    """
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    try:
        yield
    finally:
        os.environ.pop("QT_QPA_PLATFORM", None)


@pytest.fixture
def mock_notify() -> Generator[MagicMock, None, None]:
    """Mock notification system to prevent actual notifications during tests.
    
    Prevents desktop notifications from appearing while running tests.
    
    Yields:
        Mock notification function
    """
    with patch("contextipy.utils.notifications.send_notification") as mock:
        yield mock


@pytest.fixture(autouse=True)
def reset_test_environment() -> Generator[None, None, None]:
    """Auto-used fixture to reset environment between tests.
    
    This fixture runs automatically for every test to ensure a clean state.
    """
    # Store original environment
    original_env = dict(os.environ)
    
    # Set QT_QPA_PLATFORM for headless testing by default
    if "DISPLAY" not in os.environ and sys.platform != "win32":
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    
    try:
        yield
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


# Test markers for conditional execution
def pytest_configure(config: Any) -> None:
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers",
        "ui: marks tests that require GUI components"
    )
    config.addinivalue_line(
        "markers",
        "windows_only: marks tests that only run on Windows"
    )
    config.addinivalue_line(
        "markers",
        "linux_only: marks tests that only run on Linux"
    )
    config.addinivalue_line(
        "markers",
        "macos_only: marks tests that only run on macOS"
    )


def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:
    """Modify test collection to skip platform-specific tests."""
    skip_windows = pytest.mark.skip(reason="Only runs on Windows")
    skip_linux = pytest.mark.skip(reason="Only runs on Linux")
    skip_macos = pytest.mark.skip(reason="Only runs on macOS")
    
    for item in items:
        if "windows_only" in item.keywords and sys.platform != "win32":
            item.add_marker(skip_windows)
        if "linux_only" in item.keywords and sys.platform != "linux":
            item.add_marker(skip_linux)
        if "macos_only" in item.keywords and sys.platform != "darwin":
            item.add_marker(skip_macos)
