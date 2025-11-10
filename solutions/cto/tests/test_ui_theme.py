"""Tests for the UI theme module."""

from contextipy.ui import ColorPalette, Spacing, Theme, ThemeMode, Typography


def test_theme_mode_enum() -> None:
    """Test ThemeMode enum values."""
    assert ThemeMode.LIGHT.value == "light"
    assert ThemeMode.DARK.value == "dark"
    assert ThemeMode.SYSTEM.value == "system"


def test_color_palette_dataclass() -> None:
    """Test ColorPalette has expected attributes."""
    palette = ColorPalette(
        primary="#000000",
        primary_hover="#111111",
        primary_pressed="#222222",
        secondary="#333333",
        background="#444444",
        surface="#555555",
        surface_hover="#666666",
        text_primary="#777777",
        text_secondary="#888888",
        text_disabled="#999999",
        border="#aaaaaa",
        border_focus="#bbbbbb",
        success="#cccccc",
        warning="#dddddd",
        error="#eeeeee",
        info="#ffffff",
    )
    
    assert palette.primary == "#000000"
    assert palette.error == "#eeeeee"


def test_typography_dataclass() -> None:
    """Test Typography has expected attributes."""
    typography = Typography(
        font_family="Test Font",
        font_size_small=10,
        font_size_normal=12,
        font_size_medium=14,
        font_size_large=16,
        font_size_xlarge=20,
        font_weight_normal=400,
        font_weight_medium=500,
        font_weight_bold=700,
    )
    
    assert typography.font_family == "Test Font"
    assert typography.font_size_normal == 12


def test_spacing_dataclass() -> None:
    """Test Spacing has expected attributes."""
    spacing = Spacing(xs=2, sm=4, md=8, lg=12, xl=16, xxl=20)
    
    assert spacing.xs == 2
    assert spacing.xxl == 20


def test_theme_initialization() -> None:
    """Test Theme can be initialized."""
    theme = Theme(ThemeMode.LIGHT)
    
    assert theme.mode == ThemeMode.LIGHT
    assert isinstance(theme.colors, ColorPalette)
    assert isinstance(theme.typography, Typography)
    assert isinstance(theme.spacing, Spacing)


def test_theme_dark_mode() -> None:
    """Test Theme dark mode."""
    theme = Theme(ThemeMode.DARK)
    
    assert theme.mode == ThemeMode.DARK
    assert theme.colors == Theme.DARK_PALETTE


def test_theme_light_mode() -> None:
    """Test Theme light mode."""
    theme = Theme(ThemeMode.LIGHT)
    
    assert theme.mode == ThemeMode.LIGHT
    assert theme.colors == Theme.LIGHT_PALETTE


def test_theme_set_mode() -> None:
    """Test changing theme mode."""
    theme = Theme(ThemeMode.LIGHT)
    assert theme.mode == ThemeMode.LIGHT
    
    theme.set_mode(ThemeMode.DARK)
    assert theme.mode == ThemeMode.DARK
    assert theme.colors == Theme.DARK_PALETTE


def test_theme_get_stylesheet() -> None:
    """Test stylesheet generation."""
    theme = Theme(ThemeMode.LIGHT)
    stylesheet = theme.get_stylesheet()
    
    assert isinstance(stylesheet, str)
    assert len(stylesheet) > 0
    assert "QPushButton" in stylesheet
    assert "QLabel" in stylesheet
    assert theme.colors.primary in stylesheet


def test_theme_constants() -> None:
    """Test theme has expected constant palettes."""
    assert isinstance(Theme.LIGHT_PALETTE, ColorPalette)
    assert isinstance(Theme.DARK_PALETTE, ColorPalette)
    assert isinstance(Theme.TYPOGRAPHY, Typography)
    assert isinstance(Theme.SPACING, Spacing)


def test_theme_properties() -> None:
    """Test theme properties are accessible."""
    theme = Theme(ThemeMode.LIGHT)
    
    colors = theme.colors
    assert isinstance(colors, ColorPalette)
    
    typography = theme.typography
    assert isinstance(typography, Typography)
    
    spacing = theme.spacing
    assert isinstance(spacing, Spacing)
    
    mode = theme.mode
    assert isinstance(mode, ThemeMode)
