"""Tests for script_scanner module."""

from pathlib import Path

import pytest

from contextipy.scanner import (
    ScanResult,
    ScriptScanner,
    compute_file_hash,
    scan_scripts,
)


@pytest.fixture
def fixtures_path() -> Path:
    """Return the path to the test fixtures directory."""

    return Path(__file__).parent / "fixtures" / "scripts"


@pytest.fixture
def simple_script_path(fixtures_path: Path) -> Path:
    """Return the path to the simple_script fixture."""

    return fixtures_path / "simple_script.py"


class TestComputeFileHash:
    """Tests for compute_file_hash function."""

    def test_compute_hash(self, simple_script_path: Path) -> None:
        hash_value = compute_file_hash(simple_script_path)
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_hash_consistency(self, simple_script_path: Path) -> None:
        hash1 = compute_file_hash(simple_script_path)
        hash2 = compute_file_hash(simple_script_path)
        assert hash1 == hash2


class TestScriptScanner:
    """Tests for ScriptScanner class."""

    def test_scanner_initialization_single_path(self, fixtures_path: Path) -> None:
        scanner = ScriptScanner(fixtures_path)
        assert scanner.roots == (fixtures_path,)

    def test_scanner_initialization_multiple_paths(self, fixtures_path: Path) -> None:
        roots = [fixtures_path, Path("/tmp")]
        scanner = ScriptScanner(roots)
        assert len(scanner.roots) == 2

    def test_scan_simple_script(self, simple_script_path: Path) -> None:
        scanner = ScriptScanner(simple_script_path.parent)
        result = scanner.scan()
        assert result.successful()
        assert len(result.scripts) == 1

        script = result.scripts[0]
        assert script.script_id == "simple_test"
        assert script.kind == "oneshot_script"
        assert script.title == "Simple Test Script"
        assert script.description == "A simple test script for scanning"
        assert script.docstring is not None
        assert "Execute a simple test script" in script.docstring
        assert script.icon == "⚡"
        assert script.categories == ("test", "simple")
        assert script.group == ()
        assert script.accepts == ()
        assert script.timeout is None

    def test_scan_nested_directory(self, fixtures_path: Path) -> None:
        scanner = ScriptScanner(fixtures_path)
        result = scanner.scan()
        assert result.successful()
        assert len(result.scripts) >= 3

        script_ids = {s.script_id for s in result.scripts}
        assert "simple_test" in script_ids
        assert "text_to_upper" in script_ids
        assert "text_to_lower" in script_ids

    def test_scan_utilities_group(self, fixtures_path: Path) -> None:
        scanner = ScriptScanner(fixtures_path)
        result = scanner.scan()
        utilities_scripts = [s for s in result.scripts if s.group and s.group[0] == "utilities"]
        assert len(utilities_scripts) >= 2

        for script in utilities_scripts:
            assert script.group == ("utilities",)

    def test_scan_accepts_metadata(self, fixtures_path: Path) -> None:
        scanner = ScriptScanner(fixtures_path)
        result = scanner.scan()
        text_to_upper = next((s for s in result.scripts if s.script_id == "text_to_upper"), None)
        assert text_to_upper is not None
        assert text_to_upper.accepts == ("Text",)

    def test_scan_timeout_metadata(self, fixtures_path: Path) -> None:
        scanner = ScriptScanner(fixtures_path)
        result = scanner.scan()
        text_to_lower = next((s for s in result.scripts if s.script_id == "text_to_lower"), None)
        assert text_to_lower is not None
        assert text_to_lower.timeout == 5.0

    def test_scan_service(self, fixtures_path: Path) -> None:
        scanner = ScriptScanner(fixtures_path)
        result = scanner.scan()
        service = next((s for s in result.scripts if s.identifier == "example_service"), None)
        assert service is not None
        assert service.kind == "service"
        assert service.title == "Example Service"
        assert service.related_service_id is None
        assert service.group == ("services",)
        assert service.icon == "🛠"
        assert "service" in service.categories

    def test_scan_service_script(self, fixtures_path: Path) -> None:
        scanner = ScriptScanner(fixtures_path)
        result = scanner.scan()
        service_script = next(
            (s for s in result.scripts if s.script_id == "service_script_example"), None
        )
        assert service_script is not None
        assert service_script.kind == "service_script"
        assert service_script.related_service_id == "example_service"
        assert service_script.accepts == ("text",)

    def test_scan_module_icon(self, fixtures_path: Path) -> None:
        scanner = ScriptScanner(fixtures_path)
        result = scanner.scan()
        image_script = next((s for s in result.scripts if s.script_id == "resize_image"), None)
        assert image_script is not None
        assert image_script.icon == "🖼️"

    def test_scan_parameters(self, fixtures_path: Path) -> None:
        scanner = ScriptScanner(fixtures_path)
        result = scanner.scan()
        resize_script = next((s for s in result.scripts if s.script_id == "resize_image"), None)
        assert resize_script is not None
        assert "width" in resize_script.parameters
        assert "height" in resize_script.parameters

    def test_scan_file_hash_changes(self, tmp_path: Path) -> None:
        script_file = tmp_path / "test_script.py"
        script_file.write_text(
            """
from contextipy import oneshot_script

@oneshot_script(script_id="test", title="Test", description="Test script")
def test_func() -> str:
    return "test"
"""
        )

        scanner = ScriptScanner(tmp_path)
        result1 = scanner.scan()
        hash1 = result1.scripts[0].file_hash

        script_file.write_text(
            """
from contextipy import oneshot_script

@oneshot_script(script_id="test", title="Test", description="Modified test script")
def test_func() -> str:
    return "modified"
"""
        )

        result2 = scanner.scan()
        hash2 = result2.scripts[0].file_hash
        assert hash1 != hash2


class TestScanScripts:
    """Tests for scan_scripts convenience function."""

    def test_scan_scripts_wrapper(self, fixtures_path: Path) -> None:
        result = scan_scripts(fixtures_path)
        assert isinstance(result, ScanResult)
        assert len(result.scripts) > 0


class TestScanErrors:
    """Tests for error handling during scanning."""

    def test_syntax_error_handling(self, tmp_path: Path) -> None:
        bad_script = tmp_path / "bad_syntax.py"
        bad_script.write_text("def incomplete(")

        scanner = ScriptScanner(tmp_path)
        result = scanner.scan()
        assert len(result.errors) > 0
        assert result.errors[0].path == bad_script
        assert "Syntax error" in result.errors[0].message

    def test_missing_required_field(self, tmp_path: Path) -> None:
        bad_script = tmp_path / "missing_field.py"
        bad_script.write_text(
            """
from contextipy import oneshot_script

@oneshot_script(script_id="test", title="Test")
def test_func() -> str:
    return "test"
"""
        )

        scanner = ScriptScanner(tmp_path)
        result = scanner.scan()
        assert len(result.errors) > 0
