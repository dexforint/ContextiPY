# Manual Testing Instructions for Tray Shell

This document provides step-by-step instructions for manually testing the system tray implementation.

## Prerequisites

1. Ensure PySide6 is installed:
   ```bash
   pip install PySide6
   ```

2. Build/install the project:
   ```bash
   poetry install
   ```

## Running the Demo

Launch the tray demo application:

```bash
python -m contextipy.ui.tray_demo
```

Alternatively, if installed as a package:
```bash
python -c "from contextipy.ui.tray_demo import main; main()"
```

## Test Scenarios

### 1. Tray Icon Visibility

**Objective**: Verify the tray icon appears and is visible in the system tray.

**Steps**:
1. Launch the demo application
2. Look for the Contextipy icon in the system tray (usually bottom-right on Windows, top-right on macOS, varies on Linux)

**Expected Results**:
- [ ] Tray icon is visible
- [ ] Icon displays correctly (not blank or corrupted)
- [ ] Hovering over the icon shows "Contextipy" tooltip

**Troubleshooting**:
- If icon is not visible, check if system tray is supported: The app will fail if `QSystemTrayIcon.isSystemTrayAvailable()` returns False
- Some systems hide inactive tray icons - check system settings
- On Linux, ensure you have a system tray implementation (e.g., system tray extension for GNOME)

---

### 2. Context Menu Display

**Objective**: Verify the context menu appears with correct Russian-language entries.

**Steps**:
1. Right-click the tray icon
2. Observe the context menu

**Expected Results**:
- [ ] Context menu appears
- [ ] Menu entries are in Russian:
  - [ ] "Запущенные сервисы" (Running Services)
  - [ ] "Процессы" (Processes)
  - [ ] "Все скрипты и сервисы" (All Scripts and Services)
  - [ ] Separator line
  - [ ] "Настройки" (Settings)
  - [ ] "Логи" (Logs)
  - [ ] Separator line
  - [ ] "Выход" (Exit)
- [ ] Text is readable and properly encoded (no garbled characters)
- [ ] Menu is properly themed for the OS

---

### 3. Menu Action - Running Services

**Objective**: Verify the "Running Services" menu action works.

**Steps**:
1. Right-click tray icon
2. Click "Запущенные сервисы"

**Expected Results**:
- [ ] A placeholder window opens with title "Запущенные сервисы"
- [ ] Window displays description text about running services
- [ ] Window has a "Close Window" button
- [ ] Clicking "Close Window" hides the window (doesn't quit app)
- [ ] Tray icon remains visible after closing window

**Notes**: Record any issues with window appearance, positioning, or behavior.

---

### 4. Menu Action - Processes

**Objective**: Verify the "Processes" menu action works.

**Steps**:
1. Right-click tray icon
2. Click "Процессы"

**Expected Results**:
- [ ] A placeholder window opens with title "Процессы"
- [ ] Window displays description text about processes
- [ ] Window has a "Close Window" button
- [ ] Multiple windows can be open simultaneously
- [ ] Each window can be closed independently

---

### 5. Menu Action - All Scripts and Services

**Objective**: Verify the main window action works.

**Steps**:
1. Right-click tray icon
2. Click "Все скрипты и сервисы"

**Expected Results**:
- [ ] A placeholder window opens with title "Все скрипты и сервисы"
- [ ] Window displays description text about scripts and services

**Alternative Test**:
1. Double-click the tray icon

**Expected Results**:
- [ ] Same "All Scripts and Services" window opens
- [ ] Double-click behavior is consistent with menu action

---

### 6. Menu Action - Settings

**Objective**: Verify the settings window action works.

**Steps**:
1. Right-click tray icon
2. Click "Настройки"

**Expected Results**:
- [ ] A placeholder window opens with title "Настройки"
- [ ] Window displays description text about settings

---

### 7. Menu Action - Logs

**Objective**: Verify the logs window action works.

**Steps**:
1. Right-click tray icon
2. Click "Логи"

**Expected Results**:
- [ ] A placeholder window opens with title "Логи"
- [ ] Window displays description text about logs

---

### 8. Menu Action - Exit

**Objective**: Verify the exit action properly quits the application.

**Steps**:
1. Open several placeholder windows (Running Services, Processes, Logs)
2. Right-click tray icon
3. Click "Выход"
4. Observe what happens

**Expected Results**:
- [ ] All open windows close
- [ ] Tray icon disappears
- [ ] Application process terminates
- [ ] No zombie processes remain (check with Task Manager/Activity Monitor/ps)

**Cleanup Check**:
- [ ] No error messages printed to console
- [ ] No crash dialogs appear

---

### 9. Startup Notification

**Objective**: Verify the welcome notification appears on startup.

**Steps**:
1. Close the application if running
2. Launch the demo again
3. Observe system notifications

**Expected Results**:
- [ ] A balloon notification appears from the tray icon
- [ ] Notification title: "Contextipy Started"
- [ ] Notification message: "Contextipy is now running in the system tray..."
- [ ] Notification is visible for ~5 seconds
- [ ] Notification appearance matches OS style

**Platform-Specific Notes**:
- Windows: Should show as a system tray balloon
- macOS: Should show as a notification banner
- Linux: Depends on notification daemon (notify-send)

---

### 10. Notification Settings Integration

**Objective**: Verify that notification preferences are respected.

**Steps** (requires modifying settings manually or via settings window):
1. Locate the settings file:
   - Windows: `%APPDATA%\contextipy\settings.json`
   - macOS: `~/Library/Application Support/contextipy/settings.json`
   - Linux: `~/.config/contextipy/settings.json`
2. Edit the file and set `"enable_notifications": false`
3. Launch the demo

**Expected Results**:
- [ ] No welcome notification appears
- [ ] Application still starts normally
- [ ] Tray icon is visible

**Re-enable Test**:
1. While app is running, change `"enable_notifications": true`
2. Trigger an action that would show a notification

**Expected Results**:
- [ ] Notifications start appearing again without restarting

---

### 11. Error Notification Test

**Objective**: Test error notifications via logging integration.

**Steps**:
1. With the demo running, open a Python console
2. Execute:
   ```python
   import logging
   logger = logging.getLogger("contextipy.test")
   logger.error("This is a test error notification")
   ```

**Expected Results**:
- [ ] An error notification appears from the tray
- [ ] Notification has "Error" or critical icon (red)
- [ ] Notification duration is longer (~10 seconds)

---

### 12. Warning Notification Test

**Objective**: Test warning notifications via logging integration.

**Steps**:
1. With the demo running, open a Python console
2. Execute:
   ```python
   import logging
   logger = logging.getLogger("contextipy.test")
   logger.warning("This is a test warning notification")
   ```

**Expected Results**:
- [ ] A warning notification appears from the tray
- [ ] Notification has warning icon (yellow/orange)
- [ ] Notification duration is medium (~7 seconds)

---

### 13. Multi-Window Management

**Objective**: Verify multiple windows can be managed simultaneously.

**Steps**:
1. Open "Запущенные сервисы" window
2. Open "Процессы" window
3. Open "Все скрипты и сервисы" window
4. Open "Настройки" window
5. Open "Логи" window

**Expected Results**:
- [ ] All windows are visible
- [ ] Windows can be moved independently
- [ ] Clicking on a window brings it to front
- [ ] Minimizing a window doesn't quit the app
- [ ] Closing one window doesn't close others
- [ ] Tray icon remains visible with all windows open

---

### 14. Application Minimize Behavior

**Objective**: Verify minimize-to-tray behavior.

**Steps**:
1. Open any placeholder window
2. Minimize the window (click minimize button or use system minimize)
3. Check task bar/dock

**Expected Results**:
- [ ] Window minimizes to taskbar/dock OR disappears (minimize-to-tray)
- [ ] Tray icon remains visible
- [ ] Application continues running
- [ ] Can restore window from tray menu

**Note**: The exact behavior depends on OS and window manager settings.

---

### 15. Tray Icon Interaction

**Objective**: Test various tray icon interactions.

**Steps**:
1. Single-click the tray icon
2. Double-click the tray icon
3. Right-click the tray icon
4. Middle-click the tray icon (if available)

**Expected Results**:
- [ ] Single-click: No action or shows menu (OS-dependent)
- [ ] Double-click: Opens "All Scripts and Services" window
- [ ] Right-click: Opens context menu
- [ ] Middle-click: Behavior is OS-dependent (may do nothing)

---

### 16. Long-Running Test

**Objective**: Verify the application is stable over time.

**Steps**:
1. Launch the demo
2. Leave it running for 5-10 minutes
3. Occasionally interact with the tray menu
4. Open and close windows periodically

**Expected Results**:
- [ ] Application remains responsive
- [ ] No memory leaks (check with task manager)
- [ ] Tray icon doesn't disappear
- [ ] Menu continues to work
- [ ] No error messages in console

---

### 17. Rapid Menu Interaction

**Objective**: Test stability under rapid interaction.

**Steps**:
1. Rapidly right-click and close the menu 10 times
2. Rapidly open and close windows
3. Rapidly trigger different menu actions

**Expected Results**:
- [ ] No crashes
- [ ] No UI glitches
- [ ] Responsive to all actions
- [ ] No duplicate windows created

---

### 18. Service Shutdown Test

**Objective**: Verify services are stopped on quit (when integrated).

**Steps**:
1. If you have a ServiceManager integrated, start some test services
2. Click "Выход" in the tray menu
3. Check that services are stopped

**Expected Results**:
- [ ] ServiceManager.shutdown() is called
- [ ] All services stop gracefully
- [ ] Application exits cleanly

**Note**: This test requires actual service integration beyond the demo.

---

## Reporting Issues

When reporting issues, please include:

1. **Operating System**: (Windows 10/11, macOS version, Linux distro)
2. **Python Version**: Output of `python --version`
3. **PySide6 Version**: Output of `pip show PySide6`
4. **Test Scenario**: Which test failed
5. **Expected vs Actual**: What you expected and what happened
6. **Screenshots**: If relevant
7. **Console Output**: Any error messages
8. **Steps to Reproduce**: Detailed steps

## Platform-Specific Notes

### Windows
- System tray is in the bottom-right corner
- Hidden icons are in the overflow area (click arrow)
- Notifications appear as balloons from the tray

### macOS
- System tray is in the top-right corner (menu bar)
- Notifications appear as banners (top-right)
- Some menu items may need OS permissions

### Linux
- System tray varies by desktop environment
- GNOME requires "AppIndicator" extension
- KDE has built-in system tray support
- Notifications require notification daemon

## Success Criteria

All checkboxes in all test scenarios should be marked as passed for the implementation to be considered complete and functional.

## Additional Testing

For comprehensive testing:

1. Run automated tests: `pytest tests/test_ui_tray.py -v`
2. Check type hints: `mypy contextipy/ui/tray.py`
3. Check code style: `ruff check contextipy/ui/tray.py`
4. Run with different Qt themes
5. Test with high DPI displays
6. Test with multiple monitors
