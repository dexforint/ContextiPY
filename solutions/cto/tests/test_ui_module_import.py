"""Test that UI module can be imported and basic functions work without PySide6."""


def test_import_ui_module() -> None:
    """Test that UI module can be imported."""
    from contextipy import ui
    
    assert ui is not None


def test_import_theme() -> None:
    """Test theme module can be imported."""
    from contextipy.ui import ColorPalette, Spacing, Theme, ThemeMode, Typography
    
    assert ColorPalette is not None
    assert Spacing is not None
    assert Theme is not None
    assert ThemeMode is not None
    assert Typography is not None


def test_import_application() -> None:
    """Test application module can be imported."""
    from contextipy.ui import ensure_application, exit_application, run_window
    
    assert ensure_application is not None
    assert exit_application is not None
    assert run_window is not None


def test_import_icons() -> None:
    """Test icons module can be imported."""
    from contextipy.ui import (
        create_placeholder_icon,
        ensure_app_icon,
        get_standard_icons,
        load_icon,
        load_standard_icon,
    )
    
    assert load_icon is not None
    assert load_standard_icon is not None
    assert get_standard_icons is not None
    assert create_placeholder_icon is not None
    assert ensure_app_icon is not None


def test_import_widgets() -> None:
    """Test widgets module can be imported."""
    from contextipy.ui import (
        Card,
        HStack,
        Heading,
        PrimaryButton,
        SecondaryButton,
        SecondaryLabel,
        Spacer,
        VStack,
    )
    
    assert Card is not None
    assert Heading is not None
    assert SecondaryLabel is not None
    assert PrimaryButton is not None
    assert SecondaryButton is not None
    assert Spacer is not None
    assert VStack is not None
    assert HStack is not None


def test_import_async_utils() -> None:
    """Test async_utils module can be imported."""
    from contextipy.ui import FutureObserver, run_in_thread, run_in_thread_pool
    
    assert run_in_thread_pool is not None
    assert run_in_thread is not None
    assert FutureObserver is not None
