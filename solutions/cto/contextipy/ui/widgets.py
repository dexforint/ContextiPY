"""Shared UI widgets with consistent styling and behavior."""

from __future__ import annotations

from typing import Optional

try:  # pragma: no cover
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QFrame,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QSizePolicy,
        QVBoxLayout,
        QWidget,
    )
except ImportError:  # pragma: no cover
    Qt = None  # type: ignore[assignment]
    QFrame = object  # type: ignore[assignment,misc]
    QHBoxLayout = object  # type: ignore[assignment,misc]
    QLabel = object  # type: ignore[assignment,misc]
    QPushButton = object  # type: ignore[assignment,misc]
    QSizePolicy = None  # type: ignore[assignment]
    QVBoxLayout = object  # type: ignore[assignment,misc]
    QWidget = object  # type: ignore[assignment,misc]
    PYSIDE_AVAILABLE = False
else:
    PYSIDE_AVAILABLE = True

from .theme import get_theme


def _require_pyside() -> None:
    if not PYSIDE_AVAILABLE:
        raise RuntimeError("PySide6 is not available")


class Card(QFrame):
    """A card-style container widget with consistent styling."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        _require_pyside()
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        theme = get_theme()
        spacing = theme.spacing

        self.setObjectName("ContextipyCard")
        self.setProperty("variant", "card")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setContentsMargins(spacing.lg, spacing.lg, spacing.lg, spacing.lg)


class Heading(QLabel):
    """A heading label with configurable level."""

    def __init__(
        self,
        text: str = "",
        level: int = 1,
        parent: Optional[QWidget] = None,
    ) -> None:
        _require_pyside()
        super().__init__(text, parent)
        self._level = level
        self._apply_style()

    def _apply_style(self) -> None:
        level_attr = f"h{self._level}"
        self.setProperty("heading", level_attr)
        style = self.style()
        if style is not None:
            style.unpolish(self)
            style.polish(self)

    @property
    def level(self) -> int:
        return self._level

    @level.setter
    def level(self, value: int) -> None:
        self._level = value
        self._apply_style()


class SecondaryLabel(QLabel):
    """A secondary text label with muted styling."""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None) -> None:
        _require_pyside()
        super().__init__(text, parent)
        self.setProperty("secondary", True)
        style = self.style()
        if style is not None:
            style.unpolish(self)
            style.polish(self)


class PrimaryButton(QPushButton):
    """A primary action button."""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None) -> None:
        _require_pyside()
        super().__init__(text, parent)


class SecondaryButton(QPushButton):
    """A secondary action button with outlined styling."""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None) -> None:
        _require_pyside()
        super().__init__(text, parent)
        self.setProperty("secondary", True)
        style = self.style()
        if style is not None:
            style.unpolish(self)
            style.polish(self)


class Spacer(QWidget):
    """A flexible spacer widget."""

    def __init__(
        self,
        orientation: "Qt.Orientation | None" = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        _require_pyside()
        super().__init__(parent)
        if orientation is None:
            orientation = Qt.Orientation.Horizontal
        if orientation == Qt.Orientation.Horizontal:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        else:
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)


class VStack(QWidget):
    """Vertical stack layout container."""

    def __init__(
        self,
        spacing: Optional[int] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        _require_pyside()
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        if spacing is None:
            spacing = get_theme().spacing.md
        self._layout.setSpacing(spacing)
        self._layout.setContentsMargins(0, 0, 0, 0)

    def addWidget(
        self,
        widget: QWidget,
        stretch: int = 0,
        alignment: "Qt.AlignmentFlag | None" = None,
    ) -> None:
        """Add a widget to the vertical stack."""
        _require_pyside()
        if alignment is None:
            alignment = Qt.AlignmentFlag.AlignTop
        self._layout.addWidget(widget, stretch, alignment)

    def addLayout(self, layout: QVBoxLayout | QHBoxLayout, stretch: int = 0) -> None:
        """Add a layout to the vertical stack."""
        _require_pyside()
        self._layout.addLayout(layout, stretch)

    def addStretch(self, stretch: int = 1) -> None:
        """Add a stretch spacer."""
        _require_pyside()
        self._layout.addStretch(stretch)

    def addSpacing(self, size: int) -> None:
        """Add fixed spacing."""
        _require_pyside()
        self._layout.addSpacing(size)


class HStack(QWidget):
    """Horizontal stack layout container."""

    def __init__(
        self,
        spacing: Optional[int] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        _require_pyside()
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        if spacing is None:
            spacing = get_theme().spacing.md
        self._layout.setSpacing(spacing)
        self._layout.setContentsMargins(0, 0, 0, 0)

    def addWidget(
        self,
        widget: QWidget,
        stretch: int = 0,
        alignment: "Qt.AlignmentFlag | None" = None,
    ) -> None:
        """Add a widget to the horizontal stack."""
        _require_pyside()
        if alignment is None:
            alignment = Qt.AlignmentFlag.AlignLeft
        self._layout.addWidget(widget, stretch, alignment)

    def addLayout(self, layout: QVBoxLayout | QHBoxLayout, stretch: int = 0) -> None:
        """Add a layout to the horizontal stack."""
        _require_pyside()
        self._layout.addLayout(layout, stretch)

    def addStretch(self, stretch: int = 1) -> None:
        """Add a stretch spacer."""
        _require_pyside()
        self._layout.addStretch(stretch)

    def addSpacing(self, size: int) -> None:
        """Add fixed spacing."""
        _require_pyside()
        self._layout.addSpacing(size)
