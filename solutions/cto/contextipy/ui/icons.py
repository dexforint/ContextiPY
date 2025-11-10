"""Icon management and loading utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Final, Optional

try:  # pragma: no cover
    from PySide6.QtGui import QIcon, QPixmap
    from PySide6.QtWidgets import QApplication, QStyle
except ImportError:  # pragma: no cover
    QIcon = None  # type: ignore[assignment]
    QPixmap = None  # type: ignore[assignment]
    QApplication = None  # type: ignore[assignment]
    QStyle = None  # type: ignore[assignment]
    PYSIDE_AVAILABLE = False
else:
    PYSIDE_AVAILABLE = True

ICON_DIR: Final[Path] = Path(__file__).parent / "resources" / "icons"
APP_ICON_NAME: Final[str] = "app_icon"
_DEFAULT_ICON_EXTENSIONS: Final[tuple[str, ...]] = ("png", "svg", "ico")


def get_icon_path(name: str, extension: str = "png") -> Path:
    """Get the full path to an icon file."""
    return ICON_DIR / f"{name}.{extension}"


def load_icon(name: str, extension: Optional[str] = None) -> "QIcon":
    """Load an icon by name from the resources directory."""

    if not PYSIDE_AVAILABLE:
        raise RuntimeError("PySide6 is not available")

    candidates = (
        [f"{name}.{extension}"]
        if extension is not None
        else [f"{name}.{ext}" for ext in _DEFAULT_ICON_EXTENSIONS]
    )

    for candidate in candidates:
        icon_path = ICON_DIR / candidate
        if icon_path.exists():
            return QIcon(str(icon_path))

    return QIcon()


def load_standard_icon(standard_pixmap: "QStyle.StandardPixmap") -> "QIcon":  # type: ignore[name-defined]
    """Load a standard Qt icon."""

    if not PYSIDE_AVAILABLE:
        raise RuntimeError("PySide6 is not available")

    app = QApplication.instance()
    if app is not None and app.style() is not None:
        return app.style().standardIcon(standard_pixmap)
    return QIcon()


def get_standard_icons() -> dict[str, "QIcon"]:
    """Get commonly used standard icons."""

    if not PYSIDE_AVAILABLE:
        raise RuntimeError("PySide6 is not available")

    return {
        "apply": load_standard_icon(QStyle.StandardPixmap.SP_DialogApplyButton),
        "cancel": load_standard_icon(QStyle.StandardPixmap.SP_DialogCancelButton),
        "close": load_standard_icon(QStyle.StandardPixmap.SP_DialogCloseButton),
        "help": load_standard_icon(QStyle.StandardPixmap.SP_DialogHelpButton),
        "ok": load_standard_icon(QStyle.StandardPixmap.SP_DialogOkButton),
        "no": load_standard_icon(QStyle.StandardPixmap.SP_DialogNoButton),
        "yes": load_standard_icon(QStyle.StandardPixmap.SP_DialogYesButton),
        "information": load_standard_icon(QStyle.StandardPixmap.SP_MessageBoxInformation),
        "warning": load_standard_icon(QStyle.StandardPixmap.SP_MessageBoxWarning),
        "critical": load_standard_icon(QStyle.StandardPixmap.SP_MessageBoxCritical),
        "question": load_standard_icon(QStyle.StandardPixmap.SP_MessageBoxQuestion),
        "file": load_standard_icon(QStyle.StandardPixmap.SP_FileIcon),
        "directory": load_standard_icon(QStyle.StandardPixmap.SP_DirIcon),
        "trash": load_standard_icon(QStyle.StandardPixmap.SP_TrashIcon),
        "refresh": load_standard_icon(QStyle.StandardPixmap.SP_BrowserReload),
    }


def create_placeholder_icon(size: int = 64, color: str = "#2563eb") -> "QIcon":
    """Create a simple placeholder icon."""

    if not PYSIDE_AVAILABLE:
        raise RuntimeError("PySide6 is not available")

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPainter

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, size, size, size // 8, size // 8)
    painter.end()

    return QIcon(pixmap)


def ensure_app_icon() -> None:
    """Ensure the app icon directory exists and create a placeholder if needed."""
    ICON_DIR.mkdir(parents=True, exist_ok=True)

    app_icon_path = get_icon_path(APP_ICON_NAME)
    if app_icon_path.exists() or not PYSIDE_AVAILABLE:
        return

    icon = create_placeholder_icon(128)
    pixmap = icon.pixmap(128, 128)
    pixmap.save(str(app_icon_path))
