"""Example script demonstrating file processing and dependency management.

This script shows how to:
- Accept file inputs
- Declare Python package dependencies in docstrings
- Use parameters for configuration
- Return multiple action types

Requirements:
    Pillow>=10.0.0

The Requirements section above tells Contextipy to automatically install
the Pillow package before running this script. The format supports:
- Package names with version specifiers
- One requirement per line
- Comments with # character
"""

from pathlib import Path

from contextipy import Image, Param, oneshot_script
from contextipy.actions import Action, Notify, Text


@oneshot_script(
    script_id="image_info",
    title="Image Information",
    description="Display information about image files",
    accepts=[Image],
    icon="🖼️",
    categories=["examples", "files", "images"],
)
def image_info(
    selected_paths: list[Path],
    show_details: bool = Param(default=True, description="Show detailed metadata"),
) -> list[Action]:
    """Extract and display information from image files.

    Args:
        selected_paths: List of image file paths selected by the user
        show_details: Whether to show detailed metadata (default: True)

    Returns:
        Actions including notifications and text output with image information.
    """
    from PIL import Image as PILImage

    if not selected_paths:
        return [Notify(title="No Files", message="Please select image files to analyze")]

    results = []
    for image_path in selected_paths:
        try:
            with PILImage.open(image_path) as img:
                width, height = img.size
                mode = img.mode
                format_name = img.format or "Unknown"

                info_text = f"📁 {image_path.name}\n"
                info_text += f"📐 Size: {width} x {height}\n"
                info_text += f"🎨 Mode: {mode}\n"
                info_text += f"📝 Format: {format_name}\n"

                if show_details and hasattr(img, "info"):
                    info_text += "\nAdditional Info:\n"
                    for key, value in img.info.items():
                        info_text += f"  {key}: {value}\n"

                results.append(Text(content=info_text))

        except Exception as e:
            results.append(
                Notify(
                    title="Error",
                    message=f"Failed to process {image_path.name}: {str(e)}",
                )
            )

    return results
