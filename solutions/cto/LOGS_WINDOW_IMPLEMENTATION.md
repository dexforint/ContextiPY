# Logs Window Implementation

## Overview
Implemented a logs window for displaying recent script executions with filtering, details view, and repeat action functionality.

## Files Created/Modified

### New Files
1. **contextipy/ui/windows/logs.py** - Main logs window implementation
2. **tests/test_ui_windows_logs.py** - Comprehensive test suite
3. **contextipy/ui/windows/logs_demo.py** - Demo application for manual testing

### Modified Files
1. **contextipy/ui/windows/__init__.py** - Added exports for LogsWindow and LogsModel

## Features Implemented

### LogsWindow
- **Table View**: Displays execution logs with columns:
  - Run ID (shortened to 8 characters with tooltip showing full ID)
  - Script (script_id)
  - Start time (formatted as YYYY-MM-DD HH:MM:SS)
  - Duration (in seconds with 2 decimal places)
  - Status (color-coded: green for success, red for failure/error)
  - Actions (Details and Repeat buttons)

- **Filters**:
  - Status filter: All, Success, Error, Exception
  - Script filter: Dropdown with unique script IDs from logs (editable)
  - Filters update dynamically as logs are fetched

- **Refresh**: Button to manually refresh the log list

- **Error Handling**:
  - Gracefully handles missing resources (KeyError for deleted logs)
  - Handles FileNotFoundError for deleted files
  - Shows appropriate error dialogs with Russian messages
  - Catches and silently handles exceptions in refresh to prevent crashes

### LogDetailsDialog
- **Detailed View**: Shows comprehensive log information:
  - Run ID, Script ID, Status (color-coded HTML)
  - Start time, End time, Duration
  - Exit code (if available)
  - Timeout indicator (orange, if applicable)
  - Error message (red, word-wrapped, if applicable)

- **Expandable Sections**:
  - STDOUT section with toggle button (▶/▼)
  - STDERR section with toggle button (red styling)
  - Both start collapsed by default
  - Text displayed in read-only QTextEdit with max height of 200px

- **Actions**:
  - "Повторить действие" (Repeat action) button - calls callback with run_id
  - "Закрыть" (Close) button

### Integration
- Uses ExecutionLog from contextipy.logging.logger
- Callbacks:
  - `get_logs(limit, status, script_id)` - fetch logs with filtering
  - `repeat_action(run_id)` - trigger repeat execution

## Testing

### Test Coverage
- Table rendering with mock data (3 logs with different statuses)
- Empty list handling
- Repeat button triggering action handler
- Error handling for repeat failures
- Missing resource handling (FileNotFoundError, KeyError)
- Model updates
- Status and script filters
- Color-coded status display (green for success, red for error)
- Error message tooltips
- Details dialog display
- Expandable stdout/stderr sections
- Exception handling in get_logs

### Running Tests
```bash
pytest tests/test_ui_windows_logs.py -v
```

### Running Demo
```bash
python -m contextipy.ui.windows.logs_demo
```

## Design Patterns

### Following Existing Conventions
- Follows the same pattern as ProcessesWindow and ServicesWindow
- Uses Model classes (LogsModel) to hold data
- Uses theme system for consistent spacing and colors
- Uses standard widgets (Card, Heading, SecondaryLabel, PrimaryButton, SecondaryButton)
- Russian text for UI labels
- Optional dependency handling for PySide6

### Error Handling Strategy
1. **Missing Log**: Shows error dialog "Лог не найден"
2. **Missing Resources**: Catches KeyError with message about deleted log
3. **Deleted Files**: Catches FileNotFoundError with message about deleted files
4. **General Errors**: Generic error dialog with exception message
5. **Graceful Degradation**: Exceptions in refresh/fetch don't crash the window

## API Usage Example

```python
from contextipy.ui.windows.logs import LogsWindow
from contextipy.logging.logger import ExecutionLogger

logger = ExecutionLogger()

def get_logs(limit: int, status: str | None, script_id: str | None):
    if status:
        return logger.get_runs_by_status(status, limit=limit)
    elif script_id:
        return logger.get_runs_by_script(script_id, limit=limit)
    else:
        return logger.get_recent_runs(limit=limit)

def repeat_action(run_id: str) -> tuple[bool, str | None]:
    try:
        input_data = logger.rehydrate_input(run_id)
        # Execute script with input_data
        return (True, None)
    except Exception as e:
        return (False, str(e))

window = LogsWindow(
    get_logs=get_logs,
    repeat_action=repeat_action,
)
window.show()
```

## Future Enhancements
- Add pagination for large log lists
- Add export functionality (CSV, JSON)
- Add log search/filter by date range
- Add ability to delete old logs
- Add ability to compare runs
- Show actions summary in details dialog
