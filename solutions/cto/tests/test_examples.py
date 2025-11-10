"""Tests for example scripts in the examples/ directory."""

from pathlib import Path

import pytest

from contextipy.scanner import ScanResult, ScriptScanner


@pytest.fixture
def examples_path() -> Path:
    """Return the path to the examples directory."""
    return Path(__file__).parent.parent / "examples"


class TestExampleScripts:
    """Test that example scripts scan and validate correctly."""

    def test_examples_directory_exists(self, examples_path: Path) -> None:
        assert examples_path.exists()
        assert examples_path.is_dir()

    def test_scan_examples(self, examples_path: Path) -> None:
        scanner = ScriptScanner(examples_path)
        result = scanner.scan()
        assert isinstance(result, ScanResult)
        assert result.successful(), f"Scan errors: {result.errors}"
        assert len(result.scripts) > 0

    def test_hello_world_example(self, examples_path: Path) -> None:
        scanner = ScriptScanner(examples_path)
        result = scanner.scan()
        hello_scripts = [s for s in result.scripts if s.script_id == "hello_world"]
        assert len(hello_scripts) == 1
        hello = hello_scripts[0]
        assert hello.kind == "oneshot_script"
        assert hello.title == "Hello World"
        assert hello.icon == "👋"
        assert "examples" in hello.categories
        assert "greeting" in hello.categories

    def test_image_info_example(self, examples_path: Path) -> None:
        scanner = ScriptScanner(examples_path)
        result = scanner.scan()
        image_scripts = [s for s in result.scripts if s.script_id == "image_info"]
        assert len(image_scripts) == 1
        image_info = image_scripts[0]
        assert image_info.kind == "oneshot_script"
        assert image_info.title == "Image Information"
        assert image_info.accepts == ("Image",)
        assert image_info.icon == "🖼️"
        assert "show_details" in image_info.parameters

    def test_journal_service_example(self, examples_path: Path) -> None:
        scanner = ScriptScanner(examples_path)
        result = scanner.scan()
        service_scripts = [s for s in result.scripts if s.identifier == "daily_journal"]
        assert len(service_scripts) == 1
        service = service_scripts[0]
        assert service.kind == "service"
        assert service.title == "Daily Journal Service"
        assert service.icon == "🗒️"

        service_script_scripts = [s for s in result.scripts if s.script_id == "add_journal_entry"]
        assert len(service_script_scripts) == 1
        svc_script = service_script_scripts[0]
        assert svc_script.kind == "service_script"
        assert svc_script.related_service_id == "daily_journal"

    def test_backup_wizard_example(self, examples_path: Path) -> None:
        scanner = ScriptScanner(examples_path)
        result = scanner.scan()
        backup_scripts = [s for s in result.scripts if s.script_id == "backup_wizard"]
        assert len(backup_scripts) == 1
        backup = backup_scripts[0]
        assert backup.kind == "oneshot_script"
        assert backup.title == "Backup Wizard"
        assert backup.accepts == ("Folder",)
        assert "dry_run" in backup.parameters

    def test_example_categories(self, examples_path: Path) -> None:
        scanner = ScriptScanner(examples_path)
        result = scanner.scan()
        all_categories = set()
        for script in result.scripts:
            all_categories.update(script.categories)
        assert "examples" in all_categories

    def test_no_scan_errors(self, examples_path: Path) -> None:
        scanner = ScriptScanner(examples_path)
        result = scanner.scan()
        assert len(result.errors) == 0, f"Scan errors found: {result.errors}"
