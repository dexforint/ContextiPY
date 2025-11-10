# Tray Shell Implementation

## Overview

The `ui/tray.py` module provides a complete system tray integration for Contextipy, including:

- QSystemTrayIcon with Russian-language context menu
- Signal/slot integration for window launchers
- Settings integration for notification preferences
- Logging hooks for balloon notifications
- Lifecycle management (minimize-to-tray, clean exit)
- Service shutdown on quit

## Features

### Context Menu (Russian)

The tray icon provides the following menu entries:

1. **Запущенные сервисы** (Running Services) - Shows currently running services
2. **Процессы** (Processes) - Shows process information
3. **Все скрипты и сервисы** (All Scripts and Services) - Main window for browsing scripts
4. **Настройки** (Settings) - Application settings dialog
5. **Логи** (Logs) - Execution logs viewer
6. **Выход** (Exit) - Quit the application with cleanup

### Signals

The `TrayApplication` class emits the following signals:

- `show_running_services` - Request to show running services window
- `show_processes` - Request to show processes window
- `show_all_scripts_services` - Request to show all scripts and services window
- `show_settings` - Request to show settings window
- `show_logs` - Request to show logs window
- `quit_requested` - Request to quit the application

### Notification Integration

The tray application integrates with:

- **SettingsStore**: Respects `enable_notifications` setting
- **NotificationCenter**: Uses tray icon for balloon notifications
- Provides convenience methods:
  - `show_notification()` - General notification
  - `show_error_notification()` - Error notification (red icon, 10s)
  - `show_warning_notification()` - Warning notification (yellow icon, 7s)

### Lifecycle Management

The tray application handles:

- **Minimize-to-tray**: Application can minimize to tray while keeping services running
- **Double-click**: Opens the main "All Scripts and Services" window
- **Clean exit**: Stops all services and cleans up resources on quit
- **Service shutdown**: Calls `ServiceManager.shutdown()` on quit

## Usage

### Basic Usage

```python
from contextipy.ui import TrayApplication, ensure_application

# Ensure Qt application exists
app = ensure_application()

# Create tray application
tray = TrayApplication()

# Connect signals to handlers
tray.show_all_scripts_services.connect(lambda: print("Show scripts"))
tray.quit_requested.connect(app.quit)

# Run application
app.exec()
```

### With Dependencies

```python
from contextipy.config.settings import SettingsStore
from contextipy.execution.service_manager import ServiceManager
from contextipy.ui import TrayApplication, ensure_application
from contextipy.utils.notifications import get_notification_center

# Initialize components
app = ensure_application()
settings_store = SettingsStore()
service_manager = ServiceManager()
notification_center = get_notification_center(settings_provider=settings_store)

# Create tray with full integration
tray = TrayApplication(
    settings_store=settings_store,
    service_manager=service_manager,
    notification_center=notification_center,
)

# Connect handlers
tray.show_settings.connect(lambda: show_settings_dialog(settings_store))
tray.quit_requested.connect(app.quit)

# Show welcome notification
tray.show_notification("Started", "Contextipy is running in the system tray")

# Run application
app.exec()
```

### Factory Function

```python
from contextipy.ui import create_tray_application

# Create with factory
tray = create_tray_application(
    settings_store=settings_store,
    service_manager=service_manager,
    notification_center=notification_center,
)
```

## Testing

### Automated Tests

Run the test suite with pytest:

```bash
pytest tests/test_ui_tray.py -v
```

The test suite includes:
- Initialization tests
- Signal emission tests
- Settings integration tests
- Notification tests
- Lifecycle and cleanup tests
- Service shutdown tests

### Manual Testing

Run the demo application:

```bash
python -m contextipy.ui.tray_demo
```

**Manual Test Checklist:**

1. **Tray Icon Visibility**
   - [ ] Tray icon appears in system tray
   - [ ] Tray icon shows correct image
   - [ ] Tooltip shows "Contextipy" on hover

2. **Context Menu**
   - [ ] Right-click shows context menu
   - [ ] All menu entries are in Russian
   - [ ] Menu entries are in correct order
   - [ ] Separators are visible between sections

3. **Menu Actions**
   - [ ] "Запущенные сервисы" opens Running Services window
   - [ ] "Процессы" opens Processes window
   - [ ] "Все скрипты и сервисы" opens All Scripts window
   - [ ] "Настройки" opens Settings window
   - [ ] "Логи" opens Logs window
   - [ ] "Выход" closes all windows and exits application

4. **Double-Click Behavior**
   - [ ] Double-clicking tray icon opens "All Scripts and Services" window

5. **Notifications**
   - [ ] Welcome notification appears on startup
   - [ ] Notifications respect Settings (enable_notifications)
   - [ ] Error notifications show with critical icon
   - [ ] Warning notifications show with warning icon

6. **Lifecycle**
   - [ ] Closing windows doesn't quit application (minimizes to tray)
   - [ ] Quit from tray menu properly exits application
   - [ ] Services are stopped when quitting
   - [ ] Tray icon is removed when quitting

7. **Settings Integration**
   - [ ] Disabling notifications in Settings suppresses balloon messages
   - [ ] Settings changes are reflected without restarting

## Implementation Details

### Architecture

```
TrayApplication (QObject)
  ├─ QSystemTrayIcon (tray icon display)
  ├─ QMenu (context menu)
  ├─ SettingsStore (notification preferences)
  ├─ ServiceManager (service lifecycle)
  ├─ ExecutionLogger (log tracking)
  └─ NotificationCenter (balloon messages)
```

### Signal Flow

```
User Action → QAction.triggered → Signal Emission → Application Handler
```

Example:
```
User clicks "Логи" → logs_action.triggered → show_logs.emit() → _show_logs()
```

### Cleanup Sequence

When quitting:
1. Stop all services via `ServiceManager.shutdown()`
2. Stop notification worker via `NotificationCenter.stop()`
3. Emit `quit_requested` signal
4. Hide tray icon
5. Remove settings listener

### Error Handling

All cleanup operations are wrapped in try-except blocks to ensure graceful shutdown even if components fail.

## Integration Points

### With SettingsStore

The tray application listens for settings changes and updates notification behavior accordingly:

```python
def _on_settings_changed(self, settings: Settings) -> None:
    self._current_settings = settings
    # Notification center checks settings internally
```

### With ServiceManager

On quit, all services are properly shut down:

```python
def _on_quit_triggered(self) -> None:
    if self._service_manager:
        self._service_manager.shutdown()
    # ...
```

### With NotificationCenter

The tray icon is registered with the notification center for balloon messages:

```python
if self._notification_center:
    self._notification_center.set_tray_icon(self._tray_icon)
```

## Future Enhancements

Potential improvements:

1. **Dynamic menu updates**: Update "Running Services" submenu with active services
2. **Recent scripts**: Add "Recent" submenu with recently executed scripts
3. **Quick actions**: Add configurable quick actions to tray menu
4. **Status indicator**: Change tray icon based on service status
5. **Notification history**: Track and display notification history
6. **Multi-language support**: Support for additional languages beyond Russian
7. **Custom icons**: Per-action icons in the context menu

## Troubleshooting

### Tray Icon Not Visible

- Ensure system tray is supported: `QSystemTrayIcon.isSystemTrayAvailable()`
- Check if tray icon is hidden: `tray.is_visible()`
- Verify icon file exists in resources

### Notifications Not Showing

- Check Settings: `enable_notifications` must be True
- Verify tray supports messages: `tray_icon.supportsMessages()`
- Check notification center provider

### Services Not Stopping on Quit

- Verify ServiceManager is passed to TrayApplication
- Check ServiceManager.shutdown() implementation
- Review service stop timeouts

## API Reference

### TrayApplication

**Constructor:**
```python
TrayApplication(
    icon: QIcon | None = None,
    *,
    settings_store: SettingsStore | None = None,
    service_manager: ServiceManager | None = None,
    execution_logger: ExecutionLogger | None = None,
    notification_center: NotificationCenter | None = None,
)
```

**Methods:**
- `show_notification(title, message, icon=None, duration=5000)`
- `show_error_notification(title, message=None)`
- `show_warning_notification(title, message=None)`
- `hide_tray_icon()`
- `show_tray_icon()`
- `is_visible() -> bool`
- `cleanup()`

**Signals:**
- `show_running_services`
- `show_processes`
- `show_all_scripts_services`
- `show_settings`
- `show_logs`
- `quit_requested`

### create_tray_application

**Function:**
```python
create_tray_application(
    icon: QIcon | None = None,
    *,
    settings_store: SettingsStore | None = None,
    service_manager: ServiceManager | None = None,
    execution_logger: ExecutionLogger | None = None,
    notification_center: NotificationCenter | None = None,
) -> TrayApplication
```

Factory function to create a configured TrayApplication instance.
