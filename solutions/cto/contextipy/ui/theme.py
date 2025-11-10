"""Application-wide theme support for Contextipy UI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

try:  # pragma: no cover - optional dependency
    from PySide6.QtGui import QFont, QPalette
    from PySide6.QtWidgets import QApplication
except ImportError:  # pragma: no cover - optional dependency
    QApplication = None  # type: ignore[assignment]
    QFont = None  # type: ignore[assignment]
    QPalette = None  # type: ignore[assignment]
    PYSIDE_AVAILABLE = False
else:
    PYSIDE_AVAILABLE = True


class ThemeMode(Enum):
    """Theme mode enumeration."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


@dataclass
class ColorPalette:
    """Application color palette."""

    primary: str
    primary_hover: str
    primary_pressed: str
    secondary: str
    background: str
    surface: str
    surface_hover: str
    text_primary: str
    text_secondary: str
    text_disabled: str
    border: str
    border_focus: str
    success: str
    warning: str
    error: str
    info: str


@dataclass
class Typography:
    """Typography settings."""

    font_family: str
    font_size_small: int
    font_size_normal: int
    font_size_medium: int
    font_size_large: int
    font_size_xlarge: int
    font_weight_normal: int
    font_weight_medium: int
    font_weight_bold: int


@dataclass
class Spacing:
    """Layout spacing settings."""

    xs: int
    sm: int
    md: int
    lg: int
    xl: int
    xxl: int


class Theme:
    """Application theme manager."""

    LIGHT_PALETTE = ColorPalette(
        primary="#2563eb",
        primary_hover="#1d4ed8",
        primary_pressed="#1e40af",
        secondary="#64748b",
        background="#ffffff",
        surface="#f8fafc",
        surface_hover="#f1f5f9",
        text_primary="#0f172a",
        text_secondary="#475569",
        text_disabled="#cbd5e1",
        border="#e2e8f0",
        border_focus="#2563eb",
        success="#10b981",
        warning="#f59e0b",
        error="#ef4444",
        info="#3b82f6",
    )

    DARK_PALETTE = ColorPalette(
        primary="#3b82f6",
        primary_hover="#2563eb",
        primary_pressed="#1d4ed8",
        secondary="#94a3b8",
        background="#0f172a",
        surface="#1e293b",
        surface_hover="#334155",
        text_primary="#f1f5f9",
        text_secondary="#cbd5e1",
        text_disabled="#64748b",
        border="#334155",
        border_focus="#3b82f6",
        success="#10b981",
        warning="#f59e0b",
        error="#ef4444",
        info="#3b82f6",
    )

    TYPOGRAPHY = Typography(
        font_family="Segoe UI, -apple-system, BlinkMacSystemFont, sans-serif",
        font_size_small=11,
        font_size_normal=13,
        font_size_medium=14,
        font_size_large=16,
        font_size_xlarge=20,
        font_weight_normal=400,
        font_weight_medium=500,
        font_weight_bold=700,
    )

    SPACING = Spacing(
        xs=4,
        sm=8,
        md=12,
        lg=16,
        xl=24,
        xxl=32,
    )

    def __init__(self, mode: ThemeMode = ThemeMode.LIGHT) -> None:
        """Initialize theme with specified mode."""
        self._mode = mode
        self._palette = self._get_palette_for_mode(mode)

    def _get_palette_for_mode(self, mode: ThemeMode) -> ColorPalette:
        """Get color palette for the specified mode."""
        if mode == ThemeMode.DARK:
            return self.DARK_PALETTE
        elif mode == ThemeMode.SYSTEM:
            return self._detect_system_theme()
        return self.LIGHT_PALETTE

    def _detect_system_theme(self) -> ColorPalette:
        """Detect system theme and return appropriate palette."""
        if not PYSIDE_AVAILABLE:
            return self.LIGHT_PALETTE

        app = QApplication.instance()
        if app is not None:
            palette = app.palette()
            window_color = palette.color(QPalette.ColorRole.Window)
            if window_color.lightness() < 128:
                return self.DARK_PALETTE
        return self.LIGHT_PALETTE

    @property
    def mode(self) -> ThemeMode:
        """Get current theme mode."""
        return self._mode

    @property
    def colors(self) -> ColorPalette:
        """Get current color palette."""
        return self._palette

    @property
    def typography(self) -> Typography:
        """Get typography settings."""
        return self.TYPOGRAPHY

    @property
    def spacing(self) -> Spacing:
        """Get spacing settings."""
        return self.SPACING

    def set_mode(self, mode: ThemeMode) -> None:
        """Set theme mode and update palette."""
        self._mode = mode
        self._palette = self._get_palette_for_mode(mode)

    def get_stylesheet(self) -> str:
        """Generate complete stylesheet for the application."""
        c = self._palette
        t = self.TYPOGRAPHY
        s = self.SPACING

        return f"""
            /* Global Styles */
            * {{
                font-family: {t.font_family};
                font-size: {t.font_size_normal}px;
                color: {c.text_primary};
            }}

            QWidget {{
                background-color: {c.background};
                color: {c.text_primary};
            }}

            /* Main Window */
            QMainWindow {{
                background-color: {c.background};
            }}

            /* Buttons */
            QPushButton {{
                background-color: {c.primary};
                color: white;
                border: none;
                border-radius: 6px;
                padding: {s.sm}px {s.lg}px;
                font-weight: {t.font_weight_medium};
                min-height: 32px;
            }}

            QPushButton:hover {{
                background-color: {c.primary_hover};
            }}

            QPushButton:pressed {{
                background-color: {c.primary_pressed};
            }}

            QPushButton:disabled {{
                background-color: {c.surface};
                color: {c.text_disabled};
            }}

            QPushButton[secondary="true"] {{
                background-color: {c.surface};
                color: {c.text_primary};
                border: 1px solid {c.border};
            }}

            QPushButton[secondary="true"]:hover {{
                background-color: {c.surface_hover};
            }}

            /* Labels */
            QLabel {{
                background-color: transparent;
                color: {c.text_primary};
            }}

            QLabel[heading="h1"] {{
                font-size: {t.font_size_xlarge}px;
                font-weight: {t.font_weight_bold};
            }}

            QLabel[heading="h2"] {{
                font-size: {t.font_size_large}px;
                font-weight: {t.font_weight_bold};
            }}

            QLabel[heading="h3"] {{
                font-size: {t.font_size_medium}px;
                font-weight: {t.font_weight_bold};
            }}

            QLabel[secondary="true"] {{
                color: {c.text_secondary};
            }}

            QLabel[disabled="true"] {{
                color: {c.text_disabled};
            }}

            /* Cards */
            QFrame[variant="card"] {{
                background-color: {c.surface};
                border: 1px solid {c.border};
                border-radius: 8px;
            }}

            QFrame[variant="card"] QLabel {{
                background-color: transparent;
            }}

            /* Input Fields */
            QLineEdit, QTextEdit, QPlainTextEdit {{
                background-color: {c.surface};
                border: 1px solid {c.border};
                border-radius: 4px;
                padding: {s.sm}px;
                color: {c.text_primary};
            }}

            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
                border-color: {c.border_focus};
            }}

            QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
                background-color: {c.surface};
                color: {c.text_disabled};
            }}

            /* ComboBox */
            QComboBox {{
                background-color: {c.surface};
                border: 1px solid {c.border};
                border-radius: 4px;
                padding: {s.sm}px;
                min-height: 28px;
            }}

            QComboBox:focus {{
                border-color: {c.border_focus};
            }}

            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}

            QComboBox QAbstractItemView {{
                background-color: {c.surface};
                border: 1px solid {c.border};
                selection-background-color: {c.primary};
                selection-color: white;
            }}

            /* ScrollBar */
            QScrollBar:vertical {{
                background-color: {c.surface};
                width: 12px;
                margin: 0px;
            }}

            QScrollBar::handle:vertical {{
                background-color: {c.secondary};
                min-height: 20px;
                border-radius: 6px;
            }}

            QScrollBar::handle:vertical:hover {{
                background-color: {c.text_secondary};
            }}

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}

            QScrollBar:horizontal {{
                background-color: {c.surface};
                height: 12px;
                margin: 0px;
            }}

            QScrollBar::handle:horizontal {{
                background-color: {c.secondary};
                min-width: 20px;
                border-radius: 6px;
            }}

            QScrollBar::handle:horizontal:hover {{
                background-color: {c.text_secondary};
            }}

            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}

            /* GroupBox */
            QGroupBox {{
                border: 1px solid {c.border};
                border-radius: 6px;
                margin-top: {s.md}px;
                padding: {s.md}px;
                font-weight: {t.font_weight_medium};
            }}

            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 {s.xs}px;
                background-color: {c.background};
            }}

            /* TabWidget */
            QTabWidget::pane {{
                border: 1px solid {c.border};
                border-radius: 4px;
                background-color: {c.surface};
            }}

            QTabBar::tab {{
                background-color: {c.surface};
                border: 1px solid {c.border};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: {s.sm}px {s.lg}px;
                margin-right: 2px;
            }}

            QTabBar::tab:selected {{
                background-color: {c.background};
                border-bottom: 2px solid {c.primary};
            }}

            QTabBar::tab:hover {{
                background-color: {c.surface_hover};
            }}

            /* ListView / TreeView */
            QListView, QTreeView {{
                background-color: {c.surface};
                border: 1px solid {c.border};
                border-radius: 4px;
                padding: {s.xs}px;
            }}

            QListView::item, QTreeView::item {{
                padding: {s.sm}px;
                border-radius: 4px;
            }}

            QListView::item:hover, QTreeView::item:hover {{
                background-color: {c.surface_hover};
            }}

            QListView::item:selected, QTreeView::item:selected {{
                background-color: {c.primary};
                color: white;
            }}

            /* Menus */
            QMenuBar {{
                background-color: {c.surface};
                border-bottom: 1px solid {c.border};
            }}

            QMenuBar::item {{
                padding: {s.sm}px {s.md}px;
            }}

            QMenuBar::item:selected {{
                background-color: {c.surface_hover};
            }}

            QMenu {{
                background-color: {c.surface};
                border: 1px solid {c.border};
                padding: {s.xs}px;
            }}

            QMenu::item {{
                padding: {s.sm}px {s.lg}px;
                border-radius: 4px;
            }}

            QMenu::item:selected {{
                background-color: {c.primary};
                color: white;
            }}

            /* ToolTip */
            QToolTip {{
                background-color: {c.surface};
                color: {c.text_primary};
                border: 1px solid {c.border};
                padding: {s.xs}px {s.sm}px;
                border-radius: 4px;
            }}

            /* StatusBar */
            QStatusBar {{
                background-color: {c.surface};
                border-top: 1px solid {c.border};
            }}

            /* CheckBox & RadioButton */
            QCheckBox, QRadioButton {{
                spacing: {s.sm}px;
            }}

            QCheckBox::indicator, QRadioButton::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {c.border};
                background-color: {c.surface};
            }}

            QCheckBox::indicator {{
                border-radius: 4px;
            }}

            QRadioButton::indicator {{
                border-radius: 9px;
            }}

            QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
                background-color: {c.primary};
                border-color: {c.primary};
            }}

            QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
                border-color: {c.border_focus};
            }}

            /* Slider */
            QSlider::groove:horizontal {{
                height: 4px;
                background-color: {c.surface};
                border-radius: 2px;
            }}

            QSlider::handle:horizontal {{
                background-color: {c.primary};
                border: none;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }}

            QSlider::handle:horizontal:hover {{
                background-color: {c.primary_hover};
            }}

            /* ProgressBar */
            QProgressBar {{
                background-color: {c.surface};
                border: 1px solid {c.border};
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }}

            QProgressBar::chunk {{
                background-color: {c.primary};
                border-radius: 3px;
            }}
        """

    def apply_to_app(self, app: Optional[QApplication] = None) -> None:  # type: ignore[valid-type]
        """Apply theme to the application."""
        if not PYSIDE_AVAILABLE:
            raise RuntimeError("PySide6 is not available")

        if app is None:
            app = QApplication.instance()
        
        if app is None:
            raise RuntimeError("No QApplication instance found")

        stylesheet = self.get_stylesheet()
        app.setStyleSheet(stylesheet)

        font = QFont(self.TYPOGRAPHY.font_family.split(",")[0].strip())  # type: ignore[misc]
        font.setPixelSize(self.TYPOGRAPHY.font_size_normal)
        app.setFont(font)


_current_theme: Optional[Theme] = None


def get_theme() -> Theme:
    """Get the current application theme."""
    global _current_theme
    if _current_theme is None:
        _current_theme = Theme()
    return _current_theme


def set_theme(theme: Theme) -> None:
    """Set the current application theme."""
    global _current_theme
    _current_theme = theme
    if PYSIDE_AVAILABLE:
        try:
            theme.apply_to_app()
        except RuntimeError:
            pass


def initialize_theme(mode: ThemeMode = ThemeMode.LIGHT) -> Theme:
    """Initialize and apply theme to the application."""
    theme = Theme(mode)
    set_theme(theme)
    return theme
