"""Image processing test scripts."""

from contextipy import Image, oneshot_script

ICON = "🖼️"
CATEGORIES = ["media", "image"]


@oneshot_script(
    script_id="resize_image",
    title="Resize Image",
    description="Resize an image to given dimensions",
    accepts=[Image],
    timeout=10.0,
)
def resize_image(width: int, height: int) -> str:
    """Resize an image to the specified dimensions."""
    return f"Resized to {width}x{height}"
