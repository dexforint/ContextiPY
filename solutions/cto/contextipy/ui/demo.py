"""Demo window showcasing the Contextipy UI foundation."""

from __future__ import annotations

from typing import Sequence

try:  # pragma: no cover
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget
except ImportError:  # pragma: no cover
    QMainWindow = object  # type: ignore[assignment,misc]
    QVBoxLayout = object  # type: ignore[assignment,misc]
    QWidget = object  # type: ignore[assignment,misc]
    Qt = None  # type: ignore[assignment]
    PYSIDE_AVAILABLE = False
else:
    PYSIDE_AVAILABLE = True

from .application import run_window
from .icons import APP_ICON_NAME, load_icon
from .theme import ThemeMode, get_theme
from .widgets import Card, Heading, PrimaryButton, SecondaryButton, SecondaryLabel, VStack


class DemoWindow(QMainWindow):
    """A simple demonstration window verifying theme application."""

    def __init__(self) -> None:
        if not PYSIDE_AVAILABLE:
            raise RuntimeError("PySide6 is not available")

        super().__init__()
        theme = get_theme()
        spacing = theme.spacing

        self.setWindowTitle("Contextipy UI Demo")
        self.setMinimumSize(640, 420)

        icon = load_icon(APP_ICON_NAME)
        if not icon.isNull():
            self.setWindowIcon(icon)

        central_widget = QWidget(self)
        central_layout = QVBoxLayout(central_widget)
        central_layout.setSpacing(spacing.lg)
        central_layout.setContentsMargins(spacing.xl, spacing.xl, spacing.xl, spacing.xl)

        header = Heading("Contextipy UI Foundation", level=1)
        header.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        central_layout.addWidget(header)

        subtitle = SecondaryLabel("PySide6-based theming and shared widgets")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        central_layout.addWidget(subtitle)

        cards_container = VStack(parent=central_widget)
        cards_container_layout: QVBoxLayout = cards_container.layout()  # type: ignore[assignment]
        cards_container_layout.setSpacing(spacing.lg)

        feature_card = Card(parent=cards_container)
        feature_layout = QVBoxLayout(feature_card)
        feature_layout.setSpacing(spacing.md)
        feature_layout.addWidget(SecondaryLabel("Theme-aware controls"))
        primary_action = PrimaryButton("Primary Action")
        secondary_action = SecondaryButton("Secondary Action")
        feature_layout.addWidget(primary_action)
        feature_layout.addWidget(secondary_action)

        info_card = Card(parent=cards_container)
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(spacing.md)
        info_layout.addWidget(SecondaryLabel("Current theme mode:"))
        info_layout.addWidget(SecondaryLabel(theme.mode.value.title()))

        cards_container_layout.addWidget(feature_card)
        cards_container_layout.addWidget(info_card)

        central_layout.addWidget(cards_container)
        central_layout.addStretch(1)

        self.setCentralWidget(central_widget)


def main(argv: Sequence[str] | None = None, *, theme_mode: ThemeMode | None = None) -> int:
    """Launch the demo window."""

    return run_window(DemoWindow, argv=argv or [], theme_mode=theme_mode, show=True)


if __name__ == "__main__":
    raise SystemExit(main())
