# Contextipy UI Module

PySide6-based user interface foundation for Contextipy.

## Overview

This module provides a consistent, themeable UI framework built on PySide6 (Qt for Python).

## Features

### Theme System (`theme.py`)
- **Multiple modes**: Light, Dark, and System (auto-detect)
- **Comprehensive styling**: Colors, typography, spacing
- **Application-wide**: Single stylesheet applied globally
- **Easy customization**: Modify `ColorPalette`, `Typography`, or `Spacing` dataclasses

### Application Helpers (`application.py`)
- `ensure_application()`: Initialize or retrieve QApplication with theme
- `run_window()`: Convenience function to run event loop with a window
- `exit_application()`: Clean application shutdown

### Shared Widgets (`widgets.py`)
Consistent, styled components:
- `Card`: Container with surface styling
- `Heading`: Configurable heading levels (h1, h2, h3)
- `SecondaryLabel`: Muted text labels
- `PrimaryButton` / `SecondaryButton`: Styled action buttons
- `VStack` / `HStack`: Vertical/horizontal layout containers
- `Spacer`: Flexible spacing widget

### Async Utilities (`async_utils.py`)
- `run_in_thread_pool()`: Execute functions on Qt's thread pool
- `run_in_thread()`: Run functions on dedicated QThreads
- `FutureObserver`: Bridge QFuture results to Qt signals

### Icon Management (`icons.py`)
- `load_icon()`: Load custom icons from `resources/icons/`
- `load_standard_icon()`: Access Qt's built-in icons
- `get_standard_icons()`: Common icons dictionary
- `create_placeholder_icon()`: Generate colored placeholder icons

## Quick Start

### Running the Demo

```python
from contextipy.ui.demo import main

if __name__ == "__main__":
    raise SystemExit(main())
```

Or from command line:
```bash
python -m contextipy.ui.demo
```

### Creating a Simple Window

```python
from contextipy.ui import (
    Card,
    Heading,
    PrimaryButton,
    ThemeMode,
    run_window,
)
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget


class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My App")
        
        central = QWidget()
        layout = QVBoxLayout(central)
        
        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.addWidget(Heading("Hello World!"))
        card_layout.addWidget(PrimaryButton("Click Me"))
        
        layout.addWidget(card)
        self.setCentralWidget(central)


if __name__ == "__main__":
    raise SystemExit(run_window(MyWindow, theme_mode=ThemeMode.LIGHT))
```

### Applying Custom Theme

```python
from contextipy.ui import ColorPalette, Theme, ThemeMode, set_theme

# Create custom colors
custom_colors = ColorPalette(
    primary="#ff6b6b",
    primary_hover="#ff5252",
    # ... other colors
)

# Apply theme
theme = Theme(ThemeMode.LIGHT)
theme.colors = custom_colors
set_theme(theme)
```

## Architecture

### Graceful Dependency Handling

All UI modules gracefully handle missing PySide6 with try/except blocks and provide clear error messages when UI features are used without the dependency installed.

### Theme Application

1. `initialize_theme()` creates a Theme with specified mode
2. Theme generates complete QSS (Qt StyleSheet) based on colors
3. Stylesheet is applied to QApplication instance
4. Widgets use dynamic properties for variant styling

### Widget Styling

Widgets use Qt's property system for variant styling:
```python
button.setProperty("secondary", True)
button.style().unpolish(button)
button.style().polish(button)
```

This allows the stylesheet to apply different styles based on properties.

## File Structure

```
contextipy/ui/
├── __init__.py          # Public API exports
├── README.md            # This file
├── application.py       # QApplication management
├── async_utils.py       # Threading helpers
├── demo.py              # Demo window
├── icons.py             # Icon loading/management
├── theme.py             # Theme system
├── widgets.py           # Shared widgets
└── resources/
    └── icons/
        └── app_icon.svg # Application icon
```

## Dependencies

- **PySide6** >= 6.5.0 (Qt bindings)

## Testing

The UI foundation can be verified without displaying windows by importing modules and checking basic functionality. The finish tool will run tests automatically.

## Future Enhancements

- Icon themes
- Additional widget variants
- Animation support
- Plugin system for custom widgets
- Theme persistence
