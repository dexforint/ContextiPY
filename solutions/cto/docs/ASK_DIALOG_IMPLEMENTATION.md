# Ask Dialog UI Implementation

## Overview

The Ask Dialog UI provides a modal dialog for collecting structured user input from Contextipy scripts. It supports various question types with validation, help text, default values, and cancellation.

## Features

### Supported Question Types

1. **Text Input** - QLineEdit for string values
2. **Integer Numeric** - QSpinBox for integer values with bounds
3. **Float Numeric** - QDoubleSpinBox for floating-point values with bounds
4. **Enum/Choice** - QComboBox for selecting from predefined values
5. **Image File Picker** - File browser for selecting image files

### Validation

- **Required Fields** - Validates that required fields are not empty
- **Numeric Bounds** - Enforces `ge` (>=) and `le` (<=) constraints
- **Enum Values** - Ensures selected value is from the enum list
- **Real-time Feedback** - Validation errors appear below fields in red

### User Experience

- **Help Text** - Descriptions appear as tooltips on labels and widgets
- **Default Values** - Pre-populate fields with default values
- **Cancellation** - Cancel button or ESC key returns `None`
- **Keyboard Navigation** - Tab/Shift+Tab, Enter to submit, ESC to cancel
- **Scrolling** - Handles many questions with scrollable form area

## Architecture

### Components

```
contextipy/questions/
├── types.py          # Question and ImageQuery types
├── models.py         # Questions base class, Ask() function
└── ui.py             # AskDialog implementation (NEW)
```

### Flow

1. Script defines Questions dataclass with typed fields
2. `Ask(QuestionClass)` is called
3. `Questions.ui_schema()` generates widget metadata
4. `ask(schema)` creates and shows `AskDialog`
5. User fills form and clicks OK/Cancel
6. Dialog validates input
7. Returns `dict[str, Any]` or `None`
8. `Questions.validate_answers()` converts to dataclass

## Usage

### Basic Example

```python
from dataclasses import dataclass
from typing import Annotated
from contextipy.questions import Ask, Question, Questions

@dataclass
class UserInfo(Questions):
    name: Annotated[str, Question(title="Full Name")]
    age: Annotated[int, Question(title="Age", ge=18, le=120)]

# Call from script (requires QApplication)
result = Ask(UserInfo)
if result:
    print(f"Hello {result.name}, age {result.age}")
else:
    print("User cancelled")
```

### Advanced Example with All Features

```python
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated
from contextipy.questions import Ask, Question, Questions
from contextipy.questions.types import ImageQuery

class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

@dataclass
class TaskForm(Questions):
    # Required text field
    task_name: Annotated[
        str,
        Question(title="Task Name", description="Enter task description")
    ]
    
    # Numeric field with bounds
    hours: Annotated[
        float,
        Question(title="Estimated Hours", ge=0.5, le=40.0)
    ]
    
    # Enum with default
    priority: Annotated[
        Priority,
        Question(title="Priority", enum=[Priority.LOW, Priority.MEDIUM, Priority.HIGH])
    ] = Priority.MEDIUM
    
    # Optional text field
    notes: Annotated[
        str | None,
        Question(title="Notes", required=False)
    ] = None
    
    # Optional image file
    screenshot: Annotated[
        Path | None,
        ImageQuery(title="Screenshot", required=False, formats=["png", "jpg"])
    ] = None

result = Ask(TaskForm)
```

## Integration with Script Runner

### Asynchronous Invocation

The Ask dialog integrates with the script runner's subprocess execution model:

1. **Script Process** - Scripts run in isolated subprocess
2. **Dialog in Main Process** - UI dialogs must run in main Qt event loop
3. **Pre-execution Collection** - Currently, `ask_answers` are collected before script execution
4. **Future: In-script Asking** - For in-script `Ask()` calls, would need IPC to main process

### Current Workflow

```python
# In main process (before script execution)
schema = QuestionClass.ui_schema()
answers = ask(schema)  # Shows dialog, user fills form
if answers is None:
    return  # User cancelled

# Pass answers to script via ScriptInput
input_data = ScriptInput(
    file_paths=selected_files,
    parameters=params,
    ask_answers=answers  # Pre-collected answers
)

# Run script in subprocess
result = script_runner.run(metadata, input_data=input_data)

# In subprocess (script code)
def my_script(ask_answers: dict[str, Any]) -> None:
    # Receives pre-collected answers
    question_data = QuestionClass.from_answers(ask_answers)
    # Use question_data...
```

### Timeout Handling

- Dialog is modal and blocks until user responds
- Script timeout is independent of dialog time
- User has unlimited time to fill out form
- After dialog, script execution uses configured timeout

## API Reference

### `ask(schema: list[dict[str, Any]]) -> dict[str, Any] | None`

Render questions dialog and collect answers.

**Parameters:**
- `schema`: List of question descriptors from `Questions.ui_schema()`

**Returns:**
- Dictionary of answers if user clicks OK
- `None` if user cancels

**Raises:**
- `RuntimeError`: If PySide6 not available or QApplication not initialized

### `AskDialog(schema: list[dict[str, Any]], parent: QWidget | None = None)`

Modal dialog for rendering Ask questions.

**Methods:**
- `get_answers() -> dict[str, Any]`: Get all answers after dialog accepted

**Schema Format:**

```python
{
    "name": str,              # Field identifier
    "title": str,             # Display label
    "kind": str,              # "text", "image", etc.
    "required": bool,         # Whether field is mandatory
    "description": str,       # Optional help text (tooltip)
    "default": Any,           # Optional default value
    "enum": list,             # Optional enum values for combo box
    "ge": float,              # Optional minimum value (>=)
    "le": float,              # Optional maximum value (<=)
    "formats": list[str],     # For ImageQuery: file extensions
}
```

## Testing

### Unit Tests

Located in `tests/test_questions_ui.py`:

- Schema-to-widget mapping tests
- Validation logic tests
- Integration with Ask API
- Widget creation tests
- Answer extraction tests
- Error handling tests

### Manual Testing

See `docs/ASK_DIALOG_QA_CHECKLIST.md` for comprehensive manual test checklist covering:

- Widget rendering for all question types
- Validation scenarios
- User interaction flows
- Default values
- Answer collection
- Edge cases

### Running Tests

```bash
# Run all question-related tests
pytest tests/test_questions*.py

# Run only UI tests
pytest tests/test_questions_ui.py

# Run with coverage
pytest tests/test_questions_ui.py --cov=contextipy.questions.ui
```

## Implementation Notes

### Widget Selection Logic

The `_create_widget_for_question()` method determines widget type:

1. If `kind == "image"` → File picker (QLineEdit + Browse button)
2. If `enum` present → Combo box (QComboBox)
3. If `ge` or `le` present → Numeric spin box (QSpinBox or QDoubleSpinBox)
4. Default → Text input (QLineEdit)

### Validation Order

When OK is clicked, validation checks in order:

1. Required field check (not empty)
2. Numeric bounds check (ge/le)
3. Enum value check (in allowed list)

All validation errors are shown simultaneously.

### Answer Format

Answers are returned with minimal processing:

- String fields → `str`
- Integer spin boxes → `int`
- Float spin boxes → `float`
- Combo boxes → enum value string (e.g., "Color.RED")
- File pickers → `str` (file path)
- Empty optional fields → excluded from dictionary

The `Questions.validate_answers()` method handles type coercion and validation.

## Future Enhancements

### Potential Improvements

1. **In-script Asking** - Support `Ask()` calls during script execution via IPC
2. **Additional Widget Types** - Date picker, multi-line text, checkboxes
3. **Custom Validators** - User-defined validation functions
4. **Conditional Fields** - Show/hide fields based on other values
5. **Grouped Questions** - Organize questions into sections
6. **Progress Indication** - Show which step of multi-page form
7. **Theme Integration** - Apply Contextipy theme to dialog

### Async/Await Support

For truly asynchronous in-script asking:

```python
# Future potential API
async def my_async_script():
    result = await ask_async(QuestionClass)
    # Continue script with result
```

Would require:
- IPC channel between subprocess and main process
- Message queue for requests/responses
- Async event loop integration

## Troubleshooting

### Common Issues

**"PySide6 is not available"**
- Install PySide6: `pip install PySide6`

**"QApplication must be initialized"**
- Ensure `ensure_application()` is called before `Ask()`
- In tests, mock or skip UI tests

**Dialog doesn't appear**
- Check if script is in subprocess (dialogs need main process)
- Verify Qt event loop is running

**Validation always fails**
- Check question schema format
- Verify enum values match exactly
- Ensure numeric types match (int vs float)

### Debugging

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Then run Ask
result = Ask(QuestionClass)
```

## Related Documentation

- `docs/ASK_DIALOG_QA_CHECKLIST.md` - Manual testing checklist
- `contextipy/questions/demo.py` - Example usage
- `tests/test_questions_ui.py` - Test examples
- `contextipy/questions/models.py` - Questions API
- `contextipy/questions/types.py` - Question types
