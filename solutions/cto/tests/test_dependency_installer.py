"""Tests for the dependency installer module."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from contextipy.scanner.dependency_installer import (
    DependencyInstaller,
    InstallConfig,
    InstallResult,
    InstallStatus,
    PerScriptVenvStrategy,
    SharedVenvStrategy,
    compute_requirements_hash,
    parse_requirements_from_docstring,
)


class TestParseRequirementsFromDocstring:
    """Tests for parse_requirements_from_docstring function."""

    def test_empty_docstring(self) -> None:
        result = parse_requirements_from_docstring(None)
        assert result == ()

        result = parse_requirements_from_docstring("")
        assert result == ()

    def test_no_requirements_section(self) -> None:
        docstring = """This is a script without requirements.
        
        It does something useful.
        """
        result = parse_requirements_from_docstring(docstring)
        assert result == ()

    def test_basic_requirements_section(self) -> None:
        docstring = """Script with requirements.
        
        Requirements:
            requests>=2.28.0
            pandas>=1.5.0
        
        More description here.
        """
        result = parse_requirements_from_docstring(docstring)
        assert result == ("requests>=2.28.0", "pandas>=1.5.0")

    def test_requirements_with_comments(self) -> None:
        docstring = """Script with commented requirements.
        
        Requirements:
            requests>=2.28.0  # HTTP library
            pandas>=1.5.0  # Data analysis
        """
        result = parse_requirements_from_docstring(docstring)
        assert result == ("requests>=2.28.0", "pandas>=1.5.0")

    def test_requirements_with_bullet_points(self) -> None:
        docstring = """Script with bullet-style requirements.
        
        Requirements:
            - requests>=2.28.0
            - pandas>=1.5.0
            * numpy>=1.20.0
        """
        result = parse_requirements_from_docstring(docstring)
        assert result == ("requests>=2.28.0", "pandas>=1.5.0", "numpy>=1.20.0")

    def test_requirements_fenced_block(self) -> None:
        docstring = """Script with fenced requirements.
        
        ```requirements
        requests>=2.28.0
        pandas>=1.5.0
        ```
        """
        result = parse_requirements_from_docstring(docstring)
        assert result == ("requests>=2.28.0", "pandas>=1.5.0")

    def test_requirements_inline_on_same_line(self) -> None:
        docstring = """Script with inline requirement.
        
        Requirements: requests>=2.28.0
        """
        result = parse_requirements_from_docstring(docstring)
        assert result == ("requests>=2.28.0",)

    def test_requirements_deduplication(self) -> None:
        docstring = """Script with duplicate requirements.
        
        Requirements:
            requests>=2.28.0
            pandas>=1.5.0
            requests>=2.28.0
        """
        result = parse_requirements_from_docstring(docstring)
        assert result == ("requests>=2.28.0", "pandas>=1.5.0")

    def test_requirements_stops_at_next_section(self) -> None:
        docstring = """Script with multiple sections.
        
        Requirements:
            requests>=2.28.0
            pandas>=1.5.0
        
        Notes:
            This should not be included.
        """
        result = parse_requirements_from_docstring(docstring)
        assert result == ("requests>=2.28.0", "pandas>=1.5.0")

    def test_mixed_formats(self) -> None:
        docstring = """Script with mixed requirements formats.
        
        Requirements:
            requests>=2.28.0
        
        ```requirements
        pandas>=1.5.0
        ```
        """
        result = parse_requirements_from_docstring(docstring)
        assert result == ("requests>=2.28.0", "pandas>=1.5.0")


class TestComputeRequirementsHash:
    """Tests for compute_requirements_hash function."""

    def test_empty_requirements(self) -> None:
        hash_value = compute_requirements_hash(())
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64

    def test_same_requirements_same_hash(self) -> None:
        reqs = ("requests>=2.28.0", "pandas>=1.5.0")
        hash1 = compute_requirements_hash(reqs)
        hash2 = compute_requirements_hash(reqs)
        assert hash1 == hash2

    def test_different_requirements_different_hash(self) -> None:
        reqs1 = ("requests>=2.28.0", "pandas>=1.5.0")
        reqs2 = ("requests>=2.28.0", "numpy>=1.20.0")
        hash1 = compute_requirements_hash(reqs1)
        hash2 = compute_requirements_hash(reqs2)
        assert hash1 != hash2

    def test_order_independent_hash(self) -> None:
        reqs1 = ("requests>=2.28.0", "pandas>=1.5.0")
        reqs2 = ("pandas>=1.5.0", "requests>=2.28.0")
        hash1 = compute_requirements_hash(reqs1)
        hash2 = compute_requirements_hash(reqs2)
        assert hash1 == hash2


class TestSharedVenvStrategy:
    """Tests for SharedVenvStrategy."""

    def test_initialization(self, tmp_path: Path) -> None:
        venv_path = tmp_path / "shared_venv"
        strategy = SharedVenvStrategy(venv_path)
        assert strategy.get_venv_path("script1") == venv_path
        assert strategy.get_venv_path("script2") == venv_path

    def test_get_pip_executable_unix(self, tmp_path: Path) -> None:
        venv_path = tmp_path / "shared_venv"
        pip_path = venv_path / "bin" / "pip"
        pip_path.parent.mkdir(parents=True)
        pip_path.touch()

        strategy = SharedVenvStrategy(venv_path)
        assert strategy.get_pip_executable("script1") == pip_path

    def test_get_pip_executable_windows(self, tmp_path: Path) -> None:
        venv_path = tmp_path / "shared_venv"
        scripts_dir = venv_path / "Scripts"
        scripts_dir.mkdir(parents=True)
        pip_path = scripts_dir / "pip.exe"
        pip_path.touch()

        strategy = SharedVenvStrategy(venv_path)
        assert strategy.get_pip_executable("script1") == pip_path

    def test_get_pip_executable_fallback(self, tmp_path: Path) -> None:
        venv_path = tmp_path / "shared_venv"
        strategy = SharedVenvStrategy(venv_path)
        assert strategy.get_pip_executable("script1") == Path("pip")

    @patch("subprocess.run")
    def test_ensure_venv_exists_creates_venv(
        self,
        mock_run: Mock,
        tmp_path: Path,
    ) -> None:
        venv_path = tmp_path / "shared_venv"
        strategy = SharedVenvStrategy(venv_path)

        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        strategy.ensure_venv_exists("script1")

        assert mock_run.called
        args = mock_run.call_args[0][0]
        assert "-m" in args
        assert "venv" in args
        assert str(venv_path) in args

    @patch("subprocess.run")
    def test_ensure_venv_exists_skips_if_exists(
        self,
        mock_run: Mock,
        tmp_path: Path,
    ) -> None:
        venv_path = tmp_path / "shared_venv"
        venv_path.mkdir()
        strategy = SharedVenvStrategy(venv_path)

        strategy.ensure_venv_exists("script1")

        mock_run.assert_not_called()


class TestPerScriptVenvStrategy:
    """Tests for PerScriptVenvStrategy."""

    def test_initialization(self, tmp_path: Path) -> None:
        venv_root = tmp_path / "venvs"
        strategy = PerScriptVenvStrategy(venv_root)

        script1_path = strategy.get_venv_path("script1")
        script2_path = strategy.get_venv_path("script2")

        assert script1_path == venv_root / "script1"
        assert script2_path == venv_root / "script2"
        assert script1_path != script2_path

    def test_get_pip_executable_unix(self, tmp_path: Path) -> None:
        venv_root = tmp_path / "venvs"
        script_venv = venv_root / "test_script"
        pip_path = script_venv / "bin" / "pip"
        pip_path.parent.mkdir(parents=True)
        pip_path.touch()

        strategy = PerScriptVenvStrategy(venv_root)
        assert strategy.get_pip_executable("test_script") == pip_path

    @patch("subprocess.run")
    def test_ensure_venv_exists_creates_venv(
        self,
        mock_run: Mock,
        tmp_path: Path,
    ) -> None:
        venv_root = tmp_path / "venvs"
        strategy = PerScriptVenvStrategy(venv_root)

        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        strategy.ensure_venv_exists("test_script")

        assert mock_run.called
        args = mock_run.call_args[0][0]
        assert "-m" in args
        assert "venv" in args
        assert "test_script" in str(args)

    @patch("subprocess.run")
    def test_ensure_venv_exists_skips_if_exists(
        self,
        mock_run: Mock,
        tmp_path: Path,
    ) -> None:
        venv_root = tmp_path / "venvs"
        script_venv = venv_root / "test_script"
        script_venv.mkdir(parents=True)

        strategy = PerScriptVenvStrategy(venv_root)
        strategy.ensure_venv_exists("test_script")

        mock_run.assert_not_called()


class TestDependencyInstaller:
    """Tests for DependencyInstaller class."""

    @pytest.fixture
    def mock_strategy(self, tmp_path: Path) -> SharedVenvStrategy:
        venv_path = tmp_path / "venv"
        venv_path.mkdir()
        pip_path = venv_path / "bin" / "pip"
        pip_path.parent.mkdir()
        pip_path.touch()
        return SharedVenvStrategy(venv_path)

    @pytest.fixture
    def cache_dir(self, tmp_path: Path) -> Path:
        return tmp_path / "cache"

    @pytest.fixture
    def installer(
        self,
        mock_strategy: SharedVenvStrategy,
        cache_dir: Path,
    ) -> DependencyInstaller:
        config = InstallConfig(max_retries=2, retry_delay=0.1, timeout=10.0)
        return DependencyInstaller(mock_strategy, cache_dir, config)

    def test_initialization(self, installer: DependencyInstaller) -> None:
        assert installer is not None

    def test_install_no_requirements(self, installer: DependencyInstaller) -> None:
        result = installer.install_requirements("test_script", ())
        assert result.status == InstallStatus.SKIPPED
        assert result.successful()

    @patch("subprocess.run")
    def test_install_requirements_success(
        self,
        mock_run: Mock,
        installer: DependencyInstaller,
    ) -> None:
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Successfully installed requests-2.28.0",
            stderr="",
        )

        requirements = ("requests>=2.28.0",)
        result = installer.install_requirements("test_script", requirements)

        assert result.status == InstallStatus.SUCCESS
        assert result.successful()
        assert result.requirements == requirements
        assert mock_run.called

    @patch("subprocess.run")
    def test_install_requirements_cached(
        self,
        mock_run: Mock,
        installer: DependencyInstaller,
        cache_dir: Path,
    ) -> None:
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Successfully installed requests-2.28.0",
            stderr="",
        )

        requirements = ("requests>=2.28.0",)

        result1 = installer.install_requirements("test_script", requirements)
        assert result1.status == InstallStatus.SUCCESS

        result2 = installer.install_requirements("test_script", requirements)
        assert result2.status == InstallStatus.CACHED
        assert result2.successful()
        assert mock_run.call_count == 1

    @patch("subprocess.run")
    def test_install_requirements_failure(
        self,
        mock_run: Mock,
        installer: DependencyInstaller,
    ) -> None:
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="ERROR: Could not find a version that satisfies the requirement",
        )

        requirements = ("nonexistent-package>=99.99.99",)
        result = installer.install_requirements("test_script", requirements)

        assert result.status == InstallStatus.FAILED
        assert not result.successful()
        assert "pip exited with status 1" in (result.error_message or "")

    @patch("subprocess.run")
    def test_install_requirements_retry(
        self,
        mock_run: Mock,
        installer: DependencyInstaller,
    ) -> None:
        mock_run.side_effect = [
            Mock(returncode=1, stdout="", stderr="Temporary failure"),
            Mock(returncode=0, stdout="Success", stderr=""),
        ]

        requirements = ("requests>=2.28.0",)
        result = installer.install_requirements("test_script", requirements)

        assert result.status == InstallStatus.SUCCESS
        assert result.successful()
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    def test_install_requirements_timeout(
        self,
        mock_run: Mock,
        installer: DependencyInstaller,
    ) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(["pip"], 10.0)

        requirements = ("requests>=2.28.0",)
        result = installer.install_requirements("test_script", requirements)

        assert result.status == InstallStatus.FAILED
        assert not result.successful()
        assert "timed out" in (result.error_message or "").lower()

    def test_clear_cache_specific_script(
        self,
        installer: DependencyInstaller,
        cache_dir: Path,
    ) -> None:
        cache_file1 = cache_dir / "script1.json"
        cache_file2 = cache_dir / "script2.json"
        cache_file1.write_text('{"requirements_hash": "abc"}')
        cache_file2.write_text('{"requirements_hash": "def"}')

        installer.clear_cache("script1")

        assert not cache_file1.exists()
        assert cache_file2.exists()

    def test_clear_cache_all(
        self,
        installer: DependencyInstaller,
        cache_dir: Path,
    ) -> None:
        cache_file1 = cache_dir / "script1.json"
        cache_file2 = cache_dir / "script2.json"
        cache_file1.write_text('{"requirements_hash": "abc"}')
        cache_file2.write_text('{"requirements_hash": "def"}')

        installer.clear_cache()

        assert not cache_file1.exists()
        assert not cache_file2.exists()

    @patch("subprocess.run")
    def test_venv_creation_failure(
        self,
        mock_run: Mock,
        cache_dir: Path,
        tmp_path: Path,
    ) -> None:
        venv_path = tmp_path / "venv"
        strategy = SharedVenvStrategy(venv_path)

        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Failed to create venv",
        )

        installer = DependencyInstaller(strategy, cache_dir)
        result = installer.install_requirements("test_script", ("requests>=2.28.0",))

        assert result.status == InstallStatus.FAILED
        assert not result.successful()
        assert "Virtual environment creation failed" in (result.error_message or "")

    @patch("subprocess.run")
    def test_install_with_pip_args(
        self,
        mock_run: Mock,
        mock_strategy: SharedVenvStrategy,
        cache_dir: Path,
    ) -> None:
        config = InstallConfig(pip_args=("--no-cache-dir", "--upgrade"))
        installer = DependencyInstaller(mock_strategy, cache_dir, config)

        mock_run.return_value = Mock(
            returncode=0,
            stdout="Success",
            stderr="",
        )

        result = installer.install_requirements("test_script", ("requests>=2.28.0",))

        assert result.status == InstallStatus.SUCCESS
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert "--no-cache-dir" in call_args
        assert "--upgrade" in call_args


class TestInstallConfig:
    """Tests for InstallConfig dataclass."""

    def test_default_values(self) -> None:
        config = InstallConfig()
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.backoff_multiplier == 2.0
        assert config.timeout == 300.0
        assert config.pip_args == ()

    def test_custom_values(self) -> None:
        config = InstallConfig(
            max_retries=5,
            retry_delay=2.0,
            backoff_multiplier=1.5,
            timeout=600.0,
            pip_args=("--no-cache-dir",),
        )
        assert config.max_retries == 5
        assert config.retry_delay == 2.0
        assert config.backoff_multiplier == 1.5
        assert config.timeout == 600.0
        assert config.pip_args == ("--no-cache-dir",)


class TestInstallResult:
    """Tests for InstallResult dataclass."""

    def test_successful_status(self) -> None:
        result = InstallResult(InstallStatus.SUCCESS, (), "", "")
        assert result.successful()

        result = InstallResult(InstallStatus.CACHED, (), "", "")
        assert result.successful()

        result = InstallResult(InstallStatus.SKIPPED, (), "", "")
        assert result.successful()

    def test_failed_status(self) -> None:
        result = InstallResult(InstallStatus.FAILED, (), "", "", "Error")
        assert not result.successful()
