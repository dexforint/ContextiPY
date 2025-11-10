"""Tests for script scanner using temp directories and sample scripts."""

from __future__ import annotations

from pathlib import Path

import pytest

from contextipy.scanner.script_scanner import (
    ScriptScanner,
    compute_file_hash,
    scan_scripts,
)


class TestScriptScanner:
    """Test script discovery and scanning."""

    def test_scan_empty_directory(self, temp_script_dir: Path) -> None:
        """Test scanning an empty directory returns no scripts."""
        scanner = ScriptScanner(temp_script_dir)
        result = scanner.scan()

        assert result.successful()
        assert len(result.scripts) == 0
        assert len(result.errors) == 0

    def test_scan_with_sample_script(self, sample_script_file: Path) -> None:
        """Test scanning directory with a valid script."""
        scanner = ScriptScanner(sample_script_file.parent)
        result = scanner.scan()

        assert result.successful()
        assert len(result.scripts) == 1
        script = result.scripts[0]
        assert script.identifier == "sample_script"
        assert script.title == "Sample Script"
        assert script.description == "A sample script for testing"
        assert script.kind == "oneshot_script"

    def test_scan_with_service(self, sample_service_file: Path) -> None:
        """Test scanning directory with a service definition."""
        scanner = ScriptScanner(sample_service_file.parent)
        result = scanner.scan()

        assert result.successful()
        assert len(result.scripts) == 2  # service + service_script
        service = next((s for s in result.scripts if s.kind == "service"), None)
        service_script = next((s for s in result.scripts if s.kind == "service_script"), None)

        assert service is not None
        assert service.identifier == "sample_service"
        assert service_script is not None
        assert service_script.identifier == "stop_service"
        assert service_script.related_service_id == "sample_service"

    def test_scan_multiple_roots(
        self, sample_script_file: Path, sample_service_file: Path
    ) -> None:
        """Test scanning multiple root directories."""
        dir1 = sample_script_file.parent / "dir1"
        dir2 = sample_script_file.parent / "dir2"
        dir1.mkdir(exist_ok=True)
        dir2.mkdir(exist_ok=True)

        # Move sample files to different directories
        script1 = dir1 / "script1.py"
        script1.write_text(sample_script_file.read_text(), encoding="utf-8")
        script2 = dir2 / "script2.py"
        script2.write_text(sample_service_file.read_text(), encoding="utf-8")

        scanner = ScriptScanner([dir1, dir2])
        result = scanner.scan()

        assert result.successful()
        assert len(result.scripts) >= 2  # At least script1 + service from script2

    def test_scan_invalid_syntax_file(self, temp_script_dir: Path) -> None:
        """Test scanning a file with syntax errors."""
        bad_file = temp_script_dir / "bad_syntax.py"
        bad_file.write_text("def bad(:\n    pass\n", encoding="utf-8")

        scanner = ScriptScanner(temp_script_dir)
        result = scanner.scan()

        assert not result.successful()
        assert len(result.errors) == 1
        assert "Syntax error" in result.errors[0].message

    def test_scan_skips_init_files(self, temp_script_dir: Path) -> None:
        """Test that __init__.py files are skipped during scanning."""
        init_file = temp_script_dir / "__init__.py"
        init_file.write_text(
            '''"""Package init."""

from contextipy import oneshot_script

@oneshot_script(
    script_id="init_script",
    title="Init Script",
    description="Should not be scanned",
)
def init_script() -> None:
    pass
''',
            encoding="utf-8",
        )

        scanner = ScriptScanner(temp_script_dir)
        result = scanner.scan()

        assert result.successful()
        assert len(result.scripts) == 0  # __init__.py files are ignored

    def test_scan_nested_directories(self, temp_script_dir: Path) -> None:
        """Test scanning nested directory structures."""
        nested = temp_script_dir / "level1" / "level2"
        nested.mkdir(parents=True, exist_ok=True)

        nested_script = nested / "nested.py"
        nested_script.write_text(
            '''"""Nested script."""

from contextipy import oneshot_script
from contextipy.actions import Text

@oneshot_script(
    script_id="nested_script",
    title="Nested Script",
    description="Script in nested directory",
)
def nested() -> Text:
    return Text("Nested")
''',
            encoding="utf-8",
        )

        scanner = ScriptScanner(temp_script_dir)
        result = scanner.scan()

        assert result.successful()
        assert len(result.scripts) == 1
        assert result.scripts[0].identifier == "nested_script"
        assert "level1.level2" in result.scripts[0].module

    def test_scan_script_with_metadata(self, temp_script_dir: Path) -> None:
        """Test scanning script with module-level metadata."""
        script = temp_script_dir / "metadata_script.py"
        script.write_text(
            '''"""Script with metadata."""

ICON = "🔧"
CATEGORIES = ["tools", "utilities"]

from contextipy import oneshot_script
from contextipy.actions import Text

@oneshot_script(
    script_id="meta_script",
    title="Meta Script",
    description="Script with icon and categories",
)
def meta() -> Text:
    return Text("Meta")
''',
            encoding="utf-8",
        )

        scanner = ScriptScanner(temp_script_dir)
        result = scanner.scan()

        assert result.successful()
        assert len(result.scripts) == 1
        script_meta = result.scripts[0]
        assert script_meta.icon == "🔧"
        assert script_meta.categories == ("tools", "utilities")

    def test_file_hash_computation(self, sample_script_file: Path) -> None:
        """Test that file hash is computed correctly."""
        hash1 = compute_file_hash(sample_script_file)
        assert len(hash1) == 64  # SHA-256 produces 64 hex characters

        # Modify file and verify hash changes
        original_content = sample_script_file.read_text()
        sample_script_file.write_text(original_content + "\n# Modified\n", encoding="utf-8")
        hash2 = compute_file_hash(sample_script_file)

        assert hash1 != hash2

    def test_scan_convenience_function(self, sample_script_file: Path) -> None:
        """Test the scan_scripts convenience function."""
        result = scan_scripts(sample_script_file.parent)

        assert result.successful()
        assert len(result.scripts) >= 1


class TestScriptScannerProperties:
    """Test scanner properties and attributes."""

    def test_scanner_roots_property(self, temp_script_dir: Path) -> None:
        """Test that scanner exposes roots property."""
        scanner = ScriptScanner(temp_script_dir)
        assert scanner.roots == (temp_script_dir,)

    def test_scanner_multiple_roots(self, temp_script_dir: Path) -> None:
        """Test scanner with multiple root paths."""
        dir1 = temp_script_dir / "root1"
        dir2 = temp_script_dir / "root2"
        dir1.mkdir()
        dir2.mkdir()

        scanner = ScriptScanner([dir1, dir2])
        assert len(scanner.roots) == 2
        assert dir1 in scanner.roots
        assert dir2 in scanner.roots

    def test_scanner_nonexistent_root(self, temp_script_dir: Path) -> None:
        """Test scanner handles nonexistent root gracefully."""
        nonexistent = temp_script_dir / "does_not_exist"
        scanner = ScriptScanner(nonexistent)
        result = scanner.scan()

        # Should succeed without errors even though path doesn't exist
        assert result.successful()
        assert len(result.scripts) == 0
