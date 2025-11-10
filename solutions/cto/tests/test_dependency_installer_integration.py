"""Integration tests for dependency installer with registry."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from contextipy.config.persistence import ScriptRegistry
from contextipy.scanner import ScriptScanner
from contextipy.scanner.dependency_installer import (
    DependencyInstaller,
    InstallConfig,
    SharedVenvStrategy,
)
from contextipy.scanner.registry import ScriptMetadataRegistry


@pytest.fixture
def fixtures_path() -> Path:
    return Path(__file__).parent / "fixtures" / "scripts"


@pytest.fixture
def tmp_venv(tmp_path: Path) -> Path:
    venv_path = tmp_path / "test_venv"
    venv_path.mkdir()
    pip_path = venv_path / "bin" / "pip"
    pip_path.parent.mkdir()
    pip_path.touch()
    return venv_path


@pytest.fixture
def mock_strategy(tmp_venv: Path) -> SharedVenvStrategy:
    return SharedVenvStrategy(tmp_venv)


@pytest.fixture
def installer(mock_strategy: SharedVenvStrategy, tmp_path: Path) -> DependencyInstaller:
    cache_dir = tmp_path / "cache"
    config = InstallConfig(max_retries=2, retry_delay=0.1, timeout=10.0)
    return DependencyInstaller(mock_strategy, cache_dir, config)


class TestRegistryIntegration:
    """Tests for registry integration with dependency installer."""

    def test_registry_without_installer(self, fixtures_path: Path, tmp_path: Path) -> None:
        registry_db = ScriptRegistry(tmp_path / "test.db")
        scanner = ScriptScanner(fixtures_path)
        registry = ScriptMetadataRegistry(registry_db, scanner)

        result = registry.rescan()
        assert result.successful()

    @patch("subprocess.run")
    def test_registry_with_installer_no_requirements(
        self,
        mock_run: Mock,
        fixtures_path: Path,
        tmp_path: Path,
        installer: DependencyInstaller,
    ) -> None:
        registry_db = ScriptRegistry(tmp_path / "test.db")
        scanner = ScriptScanner(fixtures_path)
        registry = ScriptMetadataRegistry(registry_db, scanner, installer)

        result = registry.rescan()
        assert result.successful()

        mock_run.assert_not_called()

    @patch("subprocess.run")
    def test_registry_installs_dependencies_for_new_script(
        self,
        mock_run: Mock,
        tmp_path: Path,
        installer: DependencyInstaller,
    ) -> None:
        script_dir = tmp_path / "scripts"
        script_dir.mkdir()
        script_file = script_dir / "with_requirements.py"
        script_file.write_text(
            '''from contextipy import oneshot_script

@oneshot_script(
    script_id="with_deps",
    title="Script with deps",
    description="Test script",
)
def script_func() -> str:
    """Script with requirements.

    Requirements:
        requests>=2.28.0
        pandas>=1.5.0
    """
    return "success"
'''
        )

        mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")

        registry_db = ScriptRegistry(tmp_path / "test.db")
        scanner = ScriptScanner(script_dir)
        registry = ScriptMetadataRegistry(registry_db, scanner, installer)

        result = registry.rescan()
        assert result.successful()

        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert "install" in call_args
        assert "requests>=2.28.0" in call_args
        assert "pandas>=1.5.0" in call_args

    @patch("subprocess.run")
    def test_registry_reinstalls_on_file_change(
        self,
        mock_run: Mock,
        tmp_path: Path,
        installer: DependencyInstaller,
    ) -> None:
        script_dir = tmp_path / "scripts"
        script_dir.mkdir()
        script_file = script_dir / "with_requirements.py"
        script_file.write_text(
            '''from contextipy import oneshot_script

@oneshot_script(
    script_id="with_deps",
    title="Script with deps",
    description="Test script",
)
def script_func() -> str:
    """Script with requirements.

    Requirements:
        requests>=2.28.0
    """
    return "success"
'''
        )

        mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")

        registry_db = ScriptRegistry(tmp_path / "test.db")
        scanner = ScriptScanner(script_dir)
        registry = ScriptMetadataRegistry(registry_db, scanner, installer)

        result1 = registry.rescan()
        assert result1.successful()
        call_count_1 = mock_run.call_count

        script_file.write_text(
            '''from contextipy import oneshot_script

@oneshot_script(
    script_id="with_deps",
    title="Script with deps",
    description="Updated script",
)
def script_func() -> str:
    """Script with updated requirements.

    Requirements:
        requests>=2.28.0
        numpy>=1.20.0
    """
    return "success"
'''
        )

        installer.clear_cache("with_deps")

        result2 = registry.rescan()
        assert result2.successful()
        call_count_2 = mock_run.call_count

        assert call_count_2 > call_count_1

    @patch("subprocess.run")
    def test_registry_caches_dependencies(
        self,
        mock_run: Mock,
        tmp_path: Path,
        installer: DependencyInstaller,
    ) -> None:
        script_dir = tmp_path / "scripts"
        script_dir.mkdir()
        script_file = script_dir / "with_requirements.py"
        script_file.write_text(
            '''from contextipy import oneshot_script

@oneshot_script(
    script_id="with_deps",
    title="Script with deps",
    description="Test script",
)
def script_func() -> str:
    """Script with requirements.

    Requirements:
        requests>=2.28.0
    """
    return "success"
'''
        )

        mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")

        registry_db = ScriptRegistry(tmp_path / "test.db")
        scanner = ScriptScanner(script_dir)
        registry = ScriptMetadataRegistry(registry_db, scanner, installer)

        result1 = registry.rescan()
        assert result1.successful()
        first_call_count = mock_run.call_count

        result2 = registry.rescan()
        assert result2.successful()
        second_call_count = mock_run.call_count

        assert first_call_count == second_call_count

    @patch("subprocess.run")
    def test_registry_continues_on_install_failure(
        self,
        mock_run: Mock,
        tmp_path: Path,
        installer: DependencyInstaller,
    ) -> None:
        script_dir = tmp_path / "scripts"
        script_dir.mkdir()
        script_file = script_dir / "with_bad_requirements.py"
        script_file.write_text(
            '''from contextipy import oneshot_script

@oneshot_script(
    script_id="with_bad_deps",
    title="Script with bad deps",
    description="Test script",
)
def script_func() -> str:
    """Script with bad requirements.

    Requirements:
        nonexistent-package>=99.99.99
    """
    return "success"
'''
        )

        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="ERROR: Could not find a version",
        )

        registry_db = ScriptRegistry(tmp_path / "test.db")
        scanner = ScriptScanner(script_dir)
        registry = ScriptMetadataRegistry(registry_db, scanner, installer)

        result = registry.rescan()
        assert result.successful()

        script = registry.get_script("with_bad_deps")
        assert script is not None
