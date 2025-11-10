# All Scripts Window - Manual QA Checklist

## Overview
This document provides a comprehensive manual QA checklist for the All Scripts Window feature in Contextipy.

## Test Environment Setup

### Prerequisites
- Contextipy installed with PySide6 dependencies
- At least 3-5 test scripts registered in the system
- Scripts should have different types (oneshot_script, service, service_script)
- Scripts should be in different folder groups
- At least one script with file inputs (accepts parameter)
- At least one script without file inputs

### Setup Test Scripts
```python
# Create test scripts in your scripts directory:
# 1. scripts/test/simple_script.py (no file inputs)
# 2. scripts/test/file_processor.py (with file inputs)
# 3. scripts/test/subgroup/another_script.py (in subgroup)
# 4. scripts/utilities/helper.py (different group)
```

## Test Cases

### 1. Window Initialization
- [ ] Window opens without errors
- [ ] Window title is "Все скрипты" (All Scripts)
- [ ] Window has minimum size of 1000x600
- [ ] Application icon is displayed in title bar
- [ ] Window is centered on screen (or appropriate position)

### 2. UI Layout
- [ ] Header "Все скрипты" is displayed and centered
- [ ] Subtitle "Управление зарегистрированными скриптами и сервисами" is displayed
- [ ] "Обновить" (Refresh) button is visible in toolbar
- [ ] Refresh button has refresh icon
- [ ] Table grid is displayed with proper columns

### 3. Table Structure
- [ ] Table has 8 columns: Иконка, ID, Тип, Название, Описание, Меню, Автозапуск, Действия
- [ ] Column headers are properly labeled in Russian
- [ ] Icon column is narrow and auto-sized
- [ ] ID and Type columns are auto-sized to content
- [ ] Title and Description columns stretch to fill available space
- [ ] Menu and Startup columns are auto-sized for checkboxes
- [ ] Actions column is auto-sized for buttons
- [ ] Horizontal scrollbar appears if needed
- [ ] Vertical scrollbar appears when many scripts are present

### 4. Script Display
- [ ] All registered scripts are displayed in the table
- [ ] Script ID is correctly displayed
- [ ] Script type is translated: "Скрипт", "Сервис", "Сервис-скрипт"
- [ ] Script title is displayed correctly
- [ ] Script description is displayed correctly
- [ ] Rows alternate colors for better readability
- [ ] Single row selection is enabled

### 5. Icon Display
- [ ] Scripts with icon metadata show their icons in the Icon column
- [ ] Scripts without icons show empty icon cell (no error)
- [ ] Icon size is appropriate (not too large)
- [ ] Icons are properly aligned in cells

### 6. Grouping by Folders
- [ ] Scripts are grouped by their folder hierarchy
- [ ] Group separator rows are displayed with folder icon (📁)
- [ ] Group name shows full path: "folder1 / folder2 / folder3"
- [ ] Group separator row spans all columns
- [ ] Group separator has bold text
- [ ] Group separator has different background color
- [ ] Scripts under same group appear together
- [ ] Scripts without group are displayed at the end or beginning
- [ ] Groups are sorted alphabetically
- [ ] Scripts within groups are sorted alphabetically by title

### 7. Menu Visibility Checkbox (Column 6)
- [ ] Checkbox is displayed for each script
- [ ] Checkbox is centered in cell
- [ ] Checkbox reflects current enabled state from registry
- [ ] Clicking checkbox toggles the state
- [ ] State change persists (check by reopening window)
- [ ] Toggling checkbox updates registry immediately
- [ ] No error dialog appears on successful toggle
- [ ] Error dialog appears if toggle fails
- [ ] Checkbox state is visible (checked vs unchecked)

### 8. Startup Checkbox (Column 7)
- [ ] Checkbox is displayed for each script
- [ ] Checkbox is centered in cell
- [ ] Checkbox reflects current startup state from registry
- [ ] Clicking checkbox toggles the state
- [ ] State change persists (check by reopening window)
- [ ] Toggling checkbox updates registry immediately
- [ ] No error dialog appears on successful toggle
- [ ] Error dialog appears if toggle fails
- [ ] Checkbox state is visible (checked vs unchecked)

### 9. Parameter Editor Button (⚙)
- [ ] Parameter button (⚙) is displayed for each script
- [ ] Button tooltip shows "Параметры"
- [ ] Clicking button shows info dialog (placeholder)
- [ ] Dialog message indicates feature will be implemented
- [ ] Dialog has "OK" button
- [ ] Button is always enabled

### 10. Run Button (▶)
- [ ] Run button (▶) is displayed for each script
- [ ] Button is ENABLED for scripts without file inputs (accepts is empty)
- [ ] Button is DISABLED for scripts with file inputs (accepts is not empty)
- [ ] Enabled button tooltip shows "Запустить"
- [ ] Disabled button tooltip shows "Требуются файлы на входе"
- [ ] Clicking enabled run button executes the script
- [ ] Success dialog appears if script runs successfully
- [ ] Error dialog appears if script fails
- [ ] Dialog shows appropriate message from coordinator

### 11. Refresh/Rescan Functionality
- [ ] Clicking "Обновить" button triggers registry rescan
- [ ] Success dialog appears: "Реестр скриптов успешно обновлен"
- [ ] Table refreshes and shows updated script list
- [ ] New scripts added to filesystem are detected
- [ ] Deleted scripts are removed from list
- [ ] Modified scripts are updated
- [ ] Error dialog appears if rescan fails

### 12. Config Persistence
- [ ] Enable a script, close window, reopen → state persists
- [ ] Disable a script, close window, reopen → state persists
- [ ] Enable startup for a script, close window, reopen → state persists
- [ ] Disable startup for a script, close window, reopen → state persists
- [ ] Multiple toggle changes persist correctly
- [ ] Changes are saved to registry storage

### 13. Error Handling
- [ ] Error dialog appears with appropriate title and message
- [ ] Error dialog has red error icon
- [ ] Error dialog has "OK" button
- [ ] Window remains functional after error
- [ ] Errors don't crash the application

### 14. Empty State
- [ ] When no scripts are registered, table shows no rows
- [ ] Empty table is displayed cleanly (no errors)
- [ ] Refresh still works in empty state

### 15. Performance
- [ ] Window loads quickly (<2 seconds for ~50 scripts)
- [ ] Scrolling is smooth
- [ ] Checkbox toggles are instant
- [ ] Table updates are smooth
- [ ] No memory leaks after multiple open/close cycles

### 16. Integration with Registry
- [ ] Window correctly fetches scripts from ScriptMetadataRegistry
- [ ] set_enabled calls registry.set_enabled
- [ ] set_startup calls registry.set_startup
- [ ] rescan calls registry.rescan
- [ ] Registry changes reflect immediately in UI

### 17. Integration with Coordinator
- [ ] Run button uses ContextEntryCoordinator to execute scripts
- [ ] Script execution happens in background (non-blocking)
- [ ] Success/failure results are properly handled
- [ ] Error messages are user-friendly

### 18. Accessibility
- [ ] All buttons have tooltips
- [ ] Table can be navigated with keyboard
- [ ] Checkboxes can be toggled with keyboard
- [ ] Tab order is logical
- [ ] Screen reader compatibility (if applicable)

### 19. Theme Compatibility
- [ ] Window displays correctly in light theme
- [ ] Window displays correctly in dark theme (if implemented)
- [ ] Colors are appropriate and readable
- [ ] Contrast is sufficient
- [ ] Group separators are visually distinct

### 20. Edge Cases
- [ ] Script with very long ID displays correctly (wraps or truncates)
- [ ] Script with very long title displays correctly
- [ ] Script with very long description displays correctly
- [ ] Script with special characters in name displays correctly
- [ ] Script with empty description displays correctly
- [ ] Scripts with duplicate titles display correctly
- [ ] Very large number of scripts (100+) handles well
- [ ] Rapid checkbox toggling works correctly
- [ ] Rapid rescan clicks work correctly

## Regression Testing
After any changes to the window or related components, re-run the following critical tests:
- [ ] Checkbox persistence (enabled and startup)
- [ ] Rescan functionality
- [ ] Run button validation (file inputs check)
- [ ] Grouping display
- [ ] Error handling

## Known Limitations
Document any known limitations discovered during testing:
- Parameter editor is not yet implemented (shows placeholder dialog)
- Run button only works for scripts without file input requirements
- Icons may not display if icon files are missing

## Sign-off
- Tester Name: ___________________________
- Date: ___________________________
- Build/Version: ___________________________
- Status: ☐ Pass ☐ Fail ☐ Pass with Issues

### Issues Found
List any issues found during testing:
1. 
2. 
3. 

## Notes
Add any additional notes or observations:
