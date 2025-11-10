"""Demo application for ParamsEditorWindow."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

try:
    from PySide6.QtWidgets import QApplication
except ImportError:
    print("PySide6 is required to run this demo")
    sys.exit(1)

from contextipy.core.metadata import ParameterMetadata
from contextipy.scanner.registry import RegisteredScript, ScriptSettings
from contextipy.scanner.script_scanner import ScannedScript
from contextipy.ui.windows.params_editor import ParamsEditorWindow


def create_demo_script() -> tuple[RegisteredScript, list[ParameterMetadata]]:
    """Create a demo script with various parameter types."""
    script = RegisteredScript(
        scanned=ScannedScript(
            identifier="image-processor",
            kind="oneshot_script",
            title="Image Processor",
            description="Process and resize images with various options",
            docstring="Advanced image processing script",
            file_path=Path("/demo/scripts/image_processor.py"),
            module="scripts.image_processor",
            qualname="scripts.image_processor:process",
            group=("utilities", "image_processing"),
            accepts=("image",),
            timeout=120.0,
            related_service_id=None,
            icon="image",
            categories=("utilities", "images"),
            file_hash="demo-hash",
            parameters=("width", "height", "quality", "format", "preserve_aspect", "compression_level"),
        ),
        settings=ScriptSettings(
            enabled=True,
            startup=False,
            parameter_overrides={
                "width": 1920,
                "height": 1080,
                "quality": 90,
                "format": "JPEG",
                "preserve_aspect": True,
            },
        ),
    )

    parameters_metadata = [
        ParameterMetadata(
            name="width",
            title="Width",
            description="Target width in pixels",
            annotation=int,
            required=True,
            default=inspect.Parameter.empty,
        ),
        ParameterMetadata(
            name="height",
            title="Height",
            description="Target height in pixels",
            annotation=int,
            required=True,
            default=inspect.Parameter.empty,
        ),
        ParameterMetadata(
            name="quality",
            title="Quality",
            description="Output quality (0-100)",
            annotation=int,
            required=False,
            default=85,
        ),
        ParameterMetadata(
            name="format",
            title="Format",
            description="Output image format",
            annotation=str,
            required=False,
            default="PNG",
        ),
        ParameterMetadata(
            name="preserve_aspect",
            title="Preserve Aspect Ratio",
            description="Maintain the original aspect ratio when resizing",
            annotation=bool,
            required=False,
            default=True,
        ),
        ParameterMetadata(
            name="compression_level",
            title="Compression Level",
            description="Compression level for PNG format (0-9)",
            annotation=int,
            required=False,
            default=6,
        ),
    ]

    return script, parameters_metadata


def main() -> int:
    """Run the demo application."""
    app = QApplication(sys.argv)

    script, parameters_metadata = create_demo_script()

    def save_callback(script_id: str, params: dict) -> None:
        print(f"\n=== Parameters saved for script: {script_id} ===")
        for key, value in params.items():
            print(f"  {key}: {value!r}")
        print("=" * 50)

    editor = ParamsEditorWindow(
        script=script,
        parameters_metadata=parameters_metadata,
        save_callback=save_callback,
    )

    result = editor.exec()

    if result:
        print("\nDialog accepted - parameters saved")
        final_params = editor.get_parameters()
        print(f"Final parameters: {final_params}")
    else:
        print("\nDialog rejected - parameters not saved")

    return 0


if __name__ == "__main__":
    sys.exit(main())
