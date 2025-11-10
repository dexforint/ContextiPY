# Contextipy Examples

This directory contains example scripts demonstrating various features of the Contextipy framework.
These examples are designed to be both learning resources and templates for creating your own scripts.

## Available Examples

### Basic Examples

#### `hello_world.py`
A minimal oneshot script demonstrating:
- Basic decorator usage with `@oneshot_script`
- Multiple action returns
- Icon and category metadata

**Usage**: Run directly from the Contextipy tray menu or via `contextipy-tray`.

#### `file_processor.py`
Image processing script showing:
- File input handling via `accepts=[Image]`
- Dependency declaration with the `Requirements:` docstring section
- Script parameters with `Param()`
- Error handling and multiple file processing

**Dependencies**: Pillow (auto-installed via docstring requirements)

### Advanced Examples

#### `journal_service.py`
Background service demonstration featuring:
- Service definition with `@service`
- Service script endpoints with `@service_script`
- Persistent state management with TinyDB
- Service lifecycle and instance management

**Dependencies**: tinydb (declared via markdown code fence in docstring)

#### `ask_dialog_demo.py`
Interactive dialog example showing:
- Question-based input collection with `Ask()`
- Typed dataclass-based question schemas
- Field validation and constraints
- User cancellation handling

**Usage**: Demonstrates the full Ask dialog workflow with backup configuration.

## Running the Examples

### Via Contextipy Application

1. Copy or symlink example scripts to your scripts directory (default: `~/.contextipy/scripts/`)
2. Open the Contextipy tray application
3. Navigate to "All Scripts and Services" (Russian: "Все скрипты и сервисы")
4. Find examples under the "examples" category
5. Click to execute

### Standalone Testing

You can also test scripts directly using Python:

```python
from examples.hello_world import hello_world

actions = hello_world()
for action in actions:
    print(action)
```

## Integration with Tests

These examples complement the test fixtures in `tests/fixtures/scripts/` and can be
used with the registry scanner tests. To add examples to your test suite:

```python
from pathlib import Path
from contextipy.scanner import ScriptScanner

examples_dir = Path(__file__).parent.parent / "examples"
scanner = ScriptScanner(examples_dir)
result = scanner.scan()

assert result.successful()
assert "hello_world" in [s.script_id for s in result.scripts]
```

## Creating Your Own Scripts

Use these examples as templates:

1. **For oneshot scripts**: Start with `hello_world.py` or `file_processor.py`
2. **For services**: Use `journal_service.py` as a template
3. **For interactive dialogs**: Base your script on `ask_dialog_demo.py`

See the full documentation in `docs/` for comprehensive guides on script authoring,
dependency management, and packaging.
