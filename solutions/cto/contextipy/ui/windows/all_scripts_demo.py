"""Demo application for AllScriptsWindow with mock data."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from PySide6.QtWidgets import QApplication
except ImportError:
    print("PySide6 is required to run this demo")
    sys.exit(1)

from contextipy.scanner.registry import RegisteredScript, ScriptSettings
from contextipy.scanner.script_scanner import ScannedScript
from contextipy.ui.windows.all_scripts import AllScriptsWindow


def create_demo_scripts() -> list[RegisteredScript]:
    """Create demo scripts for testing."""
    return [
        RegisteredScript(
            scanned=ScannedScript(
                identifier="file-organizer",
                kind="oneshot_script",
                title="File Organizer",
                description="Organize files by type into folders",
                docstring="Organize selected files into categorized folders",
                file_path=Path("/demo/scripts/file_organizer.py"),
                module="scripts.file_organizer",
                qualname="scripts.file_organizer:organize",
                group=("utilities", "file_management"),
                accepts=("files",),
                timeout=None,
                related_service_id=None,
                icon="folder",
                categories=("utilities", "files"),
                file_hash="hash1",
                parameters=("target_dir",),
            ),
            settings=ScriptSettings(enabled=True, startup=False, parameter_overrides=None),
        ),
        RegisteredScript(
            scanned=ScannedScript(
                identifier="image-resizer",
                kind="oneshot_script",
                title="Image Resizer",
                description="Resize images to specified dimensions",
                docstring="Batch resize images",
                file_path=Path("/demo/scripts/image_resizer.py"),
                module="scripts.image_resizer",
                qualname="scripts.image_resizer:resize",
                group=("utilities", "image_processing"),
                accepts=("image",),
                timeout=60.0,
                related_service_id=None,
                icon="image",
                categories=("utilities", "images"),
                file_hash="hash2",
                parameters=("width", "height"),
            ),
            settings=ScriptSettings(enabled=True, startup=False, parameter_overrides={"width": 800, "height": 600}),
        ),
        RegisteredScript(
            scanned=ScannedScript(
                identifier="hello-world",
                kind="oneshot_script",
                title="Hello World",
                description="Simple greeting script",
                docstring="Display a greeting message",
                file_path=Path("/demo/scripts/hello.py"),
                module="scripts.hello",
                qualname="scripts.hello:greet",
                group=("examples",),
                accepts=(),
                timeout=None,
                related_service_id=None,
                icon=None,
                categories=("examples",),
                file_hash="hash3",
                parameters=(),
            ),
            settings=ScriptSettings(enabled=True, startup=False, parameter_overrides=None),
        ),
        RegisteredScript(
            scanned=ScannedScript(
                identifier="background-service",
                kind="service",
                title="Background Service",
                description="Long-running background service",
                docstring="Service that runs in background",
                file_path=Path("/demo/scripts/service.py"),
                module="scripts.service",
                qualname="scripts.service:BackgroundService",
                group=("services",),
                accepts=(),
                timeout=None,
                related_service_id=None,
                icon="settings",
                categories=("services",),
                file_hash="hash4",
                parameters=(),
            ),
            settings=ScriptSettings(enabled=False, startup=True, parameter_overrides=None),
        ),
        RegisteredScript(
            scanned=ScannedScript(
                identifier="api-handler",
                kind="service_script",
                title="API Handler",
                description="Handle API requests",
                docstring="Process API requests via service",
                file_path=Path("/demo/scripts/api_handler.py"),
                module="scripts.api_handler",
                qualname="scripts.api_handler:handle",
                group=("services", "api"),
                accepts=(),
                timeout=30.0,
                related_service_id="background-service",
                icon=None,
                categories=("services", "api"),
                file_hash="hash5",
                parameters=("endpoint",),
            ),
            settings=ScriptSettings(enabled=True, startup=False, parameter_overrides=None),
        ),
        RegisteredScript(
            scanned=ScannedScript(
                identifier="system-monitor",
                kind="oneshot_script",
                title="System Monitor",
                description="Monitor system resources",
                docstring="Display system resource usage",
                file_path=Path("/demo/scripts/monitor.py"),
                module="scripts.monitor",
                qualname="scripts.monitor:monitor",
                group=("system",),
                accepts=(),
                timeout=None,
                related_service_id=None,
                icon="monitor",
                categories=("system", "monitoring"),
                file_hash="hash6",
                parameters=(),
            ),
            settings=ScriptSettings(enabled=True, startup=True, parameter_overrides=None),
        ),
        RegisteredScript(
            scanned=ScannedScript(
                identifier="quick-note",
                kind="oneshot_script",
                title="Quick Note",
                description="Create a quick note",
                docstring="Quickly create and save a note",
                file_path=Path("/demo/scripts/note.py"),
                module="scripts.note",
                qualname="scripts.note:create_note",
                group=(),
                accepts=(),
                timeout=None,
                related_service_id=None,
                icon=None,
                categories=("productivity",),
                file_hash="hash7",
                parameters=(),
            ),
            settings=ScriptSettings(enabled=True, startup=False, parameter_overrides=None),
        ),
    ]


def main() -> int:
    """Run the demo application."""
    app = QApplication(sys.argv)

    demo_scripts = create_demo_scripts()

    def get_scripts_callback():
        return demo_scripts

    def rescan_callback():
        print("Rescan triggered")

    def set_enabled_callback(script_id: str, enabled: bool):
        print(f"Set enabled: {script_id} = {enabled}")
        for script in demo_scripts:
            if script.script_id == script_id:
                script.settings.enabled = enabled
                break

    def set_startup_callback(script_id: str, startup: bool):
        print(f"Set startup: {script_id} = {startup}")
        for script in demo_scripts:
            if script.script_id == script_id:
                script.settings.startup = startup
                break

    def run_script_callback(script_id: str) -> tuple[bool, str | None]:
        print(f"Run script: {script_id}")
        return (True, f"Script '{script_id}' executed successfully")

    window = AllScriptsWindow(
        get_scripts=get_scripts_callback,
        rescan=rescan_callback,
        set_enabled=set_enabled_callback,
        set_startup=set_startup_callback,
        run_script=run_script_callback,
    )

    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
