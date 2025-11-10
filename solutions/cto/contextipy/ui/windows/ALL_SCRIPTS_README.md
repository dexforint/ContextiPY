# All Scripts Window

## Overview

The `AllScriptsWindow` is a comprehensive UI component for managing all registered scripts and services in the Contextipy framework. It provides a grid-based interface for viewing, configuring, and executing scripts.

## Features

### Grid Display
- **8-column table** showing:
  1. **Icon**: Visual icon for the script (if available)
  2. **ID**: Unique script identifier
  3. **Type**: Script kind (Скрипт/Сервис/Сервис-скрипт)
  4. **Title**: Human-readable script name
  5. **Description**: Brief description of what the script does
  6. **Menu**: Checkbox to toggle menu visibility (enabled state)
  7. **Startup**: Checkbox to toggle auto-startup behavior
  8. **Actions**: Parameter editor and run buttons

### Grouping
- Scripts are automatically grouped by their folder hierarchy
- Group separators show the full path (e.g., "utilities / file_management")
- Groups are displayed with a folder icon (📁) and bold text
- Scripts are sorted alphabetically within groups

### Configuration Management
- **Menu Visibility Toggle**: Enable/disable scripts in context menus
- **Startup Toggle**: Configure scripts to run on application startup
- **Persistence**: All configuration changes are saved to the registry automatically

### Script Execution
- **Run Button**: Execute scripts directly from the UI
- **Validation**: Only scripts without file input requirements can be run
- Scripts requiring file inputs show disabled run button with tooltip
- Success/error dialogs provide feedback on execution

### Refresh/Rescan
- **"Обновить" (Refresh) Button**: Trigger registry rescan
- Discovers new scripts
- Updates modified scripts
- Removes deleted scripts
- Shows confirmation dialog on success

### Parameter Editor
- **Parameter Button** (⚙): Opens parameter editor
- Currently shows placeholder dialog (feature to be implemented)

## Usage

### Basic Usage with Registry

```python
from contextipy.scanner.registry import ScriptMetadataRegistry
from contextipy.ui.windows.all_scripts import AllScriptsWindow
from PySide6.QtWidgets import QApplication

app = QApplication([])

# Create registry
registry = ScriptMetadataRegistry()
registry.load()

# Create window with registry integration
window = AllScriptsWindow(registry=registry)
window.show()

app.exec()
```

### Usage with Custom Callbacks

```python
from contextipy.ui.windows.all_scripts import AllScriptsWindow

def get_scripts():
    # Return list of RegisteredScript objects
    return my_scripts

def rescan():
    # Trigger rescan logic
    my_registry.rescan()

def set_enabled(script_id: str, enabled: bool):
    # Handle enabled toggle
    my_registry.set_enabled(script_id, enabled)

def set_startup(script_id: str, startup: bool):
    # Handle startup toggle
    my_registry.set_startup(script_id, startup)

def run_script(script_id: str) -> tuple[bool, str | None]:
    # Execute script and return (success, message)
    return (True, "Script executed successfully")

window = AllScriptsWindow(
    get_scripts=get_scripts,
    rescan=rescan,
    set_enabled=set_enabled,
    set_startup=set_startup,
    run_script=run_script,
)
window.show()
```

### Usage with Both Registry and Coordinator

```python
from contextipy.scanner.registry import ScriptMetadataRegistry
from contextipy.execution.context_entry import ContextEntryCoordinator
from contextipy.ui.windows.all_scripts import AllScriptsWindow

# Create registry and coordinator
registry = ScriptMetadataRegistry()
registry.load()

coordinator = ContextEntryCoordinator()

# Register scripts with coordinator
for script_id, registered_script in registry.list_scripts().items():
    # Register script metadata with coordinator
    pass

# Create window with both
window = AllScriptsWindow(
    registry=registry,
    coordinator=coordinator,
)
window.show()
```

## Demo Application

Run the demo to see the window in action with sample data:

```bash
python -m contextipy.ui.windows.all_scripts_demo
```

## API Reference

### AllScriptsWindow

#### Constructor Parameters

- **registry** (`ScriptMetadataRegistry | None`): Optional registry for automatic integration
- **coordinator** (`ContextEntryCoordinator | None`): Optional coordinator for script execution
- **get_scripts** (`Callable[[], list[RegisteredScript]] | None`): Custom script fetching function
- **rescan** (`Callable[[], None] | None`): Custom rescan trigger function
- **set_enabled** (`Callable[[str, bool], None] | None`): Custom enabled state setter
- **set_startup** (`Callable[[str, bool], None] | None`): Custom startup state setter
- **run_script** (`Callable[[str], tuple[bool, str | None]] | None`): Custom script runner

#### Methods

##### Public Methods

- `show()`: Display the window
- `close()`: Close the window

##### Internal Methods (for extension)

- `_refresh_view()`: Refresh the table display
- `_update_ui()`: Update UI based on model
- `_can_run_script(script: RegisteredScript) -> bool`: Check if script can be run
- `_show_error_dialog(title: str, message: str)`: Display error dialog
- `_show_info_dialog(title: str, message: str)`: Display info dialog

### ScriptModel

Data model holding the list of scripts.

#### Methods

- `update_scripts(scripts: list[RegisteredScript])`: Update the script list

## Integration Points

### With ScriptMetadataRegistry

The window integrates seamlessly with `ScriptMetadataRegistry`:
- Fetches scripts via `registry.list_scripts()`
- Triggers rescan via `registry.rescan()`
- Updates settings via `registry.set_enabled()` and `registry.set_startup()`
- Changes persist automatically through registry's storage

### With ContextEntryCoordinator

The window can execute scripts through `ContextEntryCoordinator`:
- Runs scripts via `coordinator.execute_script()`
- Handles script registration
- Manages service dependencies
- Returns execution results

## Script Validation Rules

### Run Button Enablement

The run button follows these rules:
1. **Enabled**: Script has no file input requirements (`accepts` is empty)
2. **Disabled**: Script requires file inputs (`accepts` is not empty)

Scripts requiring file inputs should be invoked from context menus with actual file selections.

## Styling

The window uses Contextipy's theme system:
- Consistent colors and spacing
- Alternating row colors in table
- Proper button styling (primary/secondary)
- Dialog styling
- Group separator styling

## Testing

### Unit Tests

Run unit tests:
```bash
pytest tests/test_ui_windows_all_scripts.py
```

### Manual QA

Follow the comprehensive QA checklist:
```
docs/ALL_SCRIPTS_WINDOW_QA.md
```

## Future Enhancements

Planned features:
1. **Parameter Editor Dialog**: Full-featured parameter configuration UI
2. **Filtering**: Filter scripts by type, group, or category
3. **Search**: Search scripts by ID, title, or description
4. **Bulk Actions**: Select multiple scripts for bulk enable/disable
5. **Export/Import**: Export/import script configurations
6. **Script Details View**: Detailed view with parameters, docstring, etc.
7. **Execution History**: View past execution results
8. **Drag and Drop**: Reorder scripts or assign to groups

## Dependencies

- PySide6: Qt bindings for UI
- contextipy.scanner.registry: Script metadata management
- contextipy.execution.context_entry: Script execution
- contextipy.ui.theme: Theming system
- contextipy.ui.widgets: UI components
- contextipy.ui.icons: Icon management

## Error Handling

The window handles errors gracefully:
- Registry errors: Shows error dialog, window remains functional
- Execution errors: Shows error dialog with message
- UI errors: Catches exceptions to prevent crashes
- Missing icons: Displays empty icon cell without errors

## Accessibility

- All buttons have tooltips
- Keyboard navigation support
- Clear visual feedback for actions
- Screen reader compatible labels (Qt accessibility)

## Performance Considerations

- Efficient table updates (only refreshes on demand)
- Lazy loading of icons
- Minimal memory footprint
- Handles 100+ scripts smoothly

## License

Part of the Contextipy project. See project LICENSE for details.
