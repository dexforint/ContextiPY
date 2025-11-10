"""UI module for Contextipy - PySide6-based user interface foundation."""

from .application import ensure_application, exit_application, run_window
from .async_utils import FutureObserver, run_in_thread, run_in_thread_pool
from .icons import (
    create_placeholder_icon,
    ensure_app_icon,
    get_standard_icons,
    load_icon,
    load_standard_icon,
)
from .theme import (
    ColorPalette,
    Spacing,
    Theme,
    ThemeMode,
    Typography,
    get_theme,
    initialize_theme,
    set_theme,
)
from .tray import TrayApplication, create_tray_application
from .widgets import (
    Card,
    HStack,
    Heading,
    PrimaryButton,
    SecondaryButton,
    SecondaryLabel,
    Spacer,
    VStack,
)

__all__ = [
    "ColorPalette",
    "Spacing",
    "Theme",
    "ThemeMode",
    "Typography",
    "get_theme",
    "initialize_theme",
    "set_theme",
    "ensure_application",
    "run_window",
    "exit_application",
    "TrayApplication",
    "create_tray_application",
    "load_icon",
    "load_standard_icon",
    "get_standard_icons",
    "create_placeholder_icon",
    "ensure_app_icon",
    "run_in_thread_pool",
    "run_in_thread",
    "FutureObserver",
    "Card",
    "Heading",
    "SecondaryLabel",
    "PrimaryButton",
    "SecondaryButton",
    "Spacer",
    "VStack",
    "HStack",
]
