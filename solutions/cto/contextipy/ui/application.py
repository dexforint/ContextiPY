"""Application helpers for initializing and running PySide6 UI components."""

from __future__ import annotations

import sys
from typing import Callable, Sequence

try:  # pragma: no cover
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication, QWidget
except ImportError:  # pragma: no cover
    QApplication = None  # type: ignore[assignment]
    QWidget = None  # type: ignore[assignment]
    QIcon = None  # type: ignore[assignment]
    Qt = None  # type: ignore[assignment]
    PYSIDE_AVAILABLE = False
else:
    PYSIDE_AVAILABLE = True

from .icons import APP_ICON_NAME, load_icon
from .theme import ThemeMode, get_theme, set_theme

_APP_NAME = "Contextipy"
_ORGANIZATION_NAME = "Contextipy"
_ORGANIZATION_DOMAIN = "contextipy.app"


def ensure_application(
    argv: Sequence[str] | None = None,
    *,
    theme_mode: ThemeMode | None = None,
    icon: QIcon | None = None,
) -> "QApplication":
    """Ensure a :class:`QApplication` exists and apply the configured theme.

    Args:
        argv: Command-line arguments to initialize the QApplication with.
        theme_mode: Optional theme mode override.
        icon: Optional application icon to set globally.

    Returns:
        The active QApplication instance.
    """

    if not PYSIDE_AVAILABLE:
        raise RuntimeError("PySide6 is not available")

    app = QApplication.instance()
    args = list(argv) if argv is not None else sys.argv

    if app is None:
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
        app = QApplication(args)
        app.setApplicationName(_APP_NAME)
        app.setOrganizationName(_ORGANIZATION_NAME)
        app.setOrganizationDomain(_ORGANIZATION_DOMAIN)
        app.setQuitOnLastWindowClosed(False)

    theme = get_theme()
    if theme_mode is not None and theme.mode is not theme_mode:
        theme.set_mode(theme_mode)
    theme.apply_to_app(app)
    set_theme(theme)

    if icon is not None:
        app.setWindowIcon(icon)
    else:
        default_icon = load_icon(APP_ICON_NAME)
        if not default_icon.isNull():
            app.setWindowIcon(default_icon)

    return app


WidgetFactory = Callable[[], "QWidget"]


def run_window(
    window: "QWidget | WidgetFactory",
    *,
    argv: Sequence[str] | None = None,
    theme_mode: ThemeMode | None = None,
    icon: QIcon | None = None,
    show: bool = True,
) -> int:
    """Run the Qt application event loop with the provided window.

    Args:
        window: Window instance or factory callable that returns a window.
        argv: Optional command-line arguments for QApplication initialization.
        theme_mode: Optional theme mode override for the application.
        icon: Optional window icon to apply before showing.
        show: Whether to automatically show the window before starting the loop.

    Returns:
        The application's exit code.
    """

    if not PYSIDE_AVAILABLE:
        raise RuntimeError("PySide6 is not available")

    app = ensure_application(argv, theme_mode=theme_mode, icon=icon)

    target_window = window() if callable(window) else window
    if target_window.windowIcon().isNull():
        target_window.setWindowIcon(icon or load_icon(APP_ICON_NAME))

    if show and not target_window.isVisible():
        target_window.show()

    return app.exec()


def exit_application(exit_code: int = 0) -> None:
    """Exit the Qt application event loop if running."""

    if not PYSIDE_AVAILABLE:
        return

    app = QApplication.instance()
    if app is not None:
        app.exit(exit_code)
