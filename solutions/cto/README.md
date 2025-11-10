# Contextipy

Contextipy is a context-aware productivity assistant that lives in your system tray. It enables you to create, deploy, and manage Python-based automation scripts with rich UI integration, dependency management, and service lifecycle control.

## Features

- **📜 Script System**: Write Python scripts that respond to context (files, text, URLs)
- **🔧 Dependency Management**: Automatic installation of script dependencies via docstring declarations
- **🎯 Background Services**: Long-running services with managed lifecycle
- **💬 Interactive Dialogs**: Question-based input collection with type validation
- **🎨 System Tray UI**: Native integration with bilingual menu support (Russian/English)
- **📦 Action System**: Unified API for file operations, notifications, clipboard, and more
- **🔍 Registry Scanner**: Automatic discovery and hot-reload of script changes

## Quick Start

### Installation

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode with dependencies
pip install -e .

# Run the tray application
contextipy-tray
```

The application starts in the system tray. Right-click the tray icon to access:
- **Запущенные сервисы** (Running Services)
- **Процессы** (Processes)
- **Все скрипты и сервисы** (All Scripts and Services)
- **Настройки** (Settings)
- **Логи** (Logs)

### Your First Script

Create a script in `~/.contextipy/scripts/my_script.py`:

```python
from contextipy import oneshot_script
from contextipy.actions import Text, Notify

@oneshot_script(
    script_id="hello",
    title="Hello Script",
    description="Say hello",
    icon="👋",
)
def hello() -> list:
    """A simple greeting script."""
    return [
        Notify(title="Hello!", message="Script executed successfully"),
        Text(content="Hello from Contextipy!"),
    ]
```

The script will automatically appear in the tray menu under "All Scripts and Services".

## Script Authoring

### Oneshot Scripts

Oneshot scripts execute once per invocation and return actions:

```python
from pathlib import Path
from contextipy import oneshot_script, Text
from contextipy.actions import Copy, Notify

@oneshot_script(
    script_id="text_to_upper",
    title="Convert to Uppercase",
    description="Convert selected text to uppercase",
    accepts=[Text],  # Accepts text as input
    categories=["text", "utilities"],
)
def to_upper(text: str) -> list:
    """Convert text to uppercase.
    
    Args:
        text: The input text from the user's selection
        
    Returns:
        Actions to copy the result and notify the user
    """
    result = text.upper()
    return [
        Copy(text=result),
        Notify(title="Converted", message="Text copied to clipboard"),
    ]
```

### Dependency Management via Docstrings

Declare dependencies directly in your script's docstring:

```python
"""Image resizer script.

Requirements:
    Pillow>=10.0.0
    numpy>=1.24.0
"""

from contextipy import oneshot_script, Image
from PIL import Image as PILImage

@oneshot_script(
    script_id="resize_image",
    title="Resize Image",
    description="Resize images to specified dimensions",
    accepts=[Image],
)
def resize_image(selected_paths: list, width: int = 800, height: int = 600):
    """Resize images using Pillow."""
    # Implementation here
    pass
```

Alternative fenced format:

```python
"""
Image processor with dependencies.

```requirements
Pillow>=10.0.0
numpy>=1.24.0
```
"""
```

Contextipy automatically creates virtual environments and installs requirements before execution. See `docs/dependency_installer.md` for details.

### Script Parameters

Use `Param()` to define configurable parameters:

```python
from contextipy import Param, oneshot_script

@oneshot_script(
    script_id="backup",
    title="Backup Files",
    description="Create a backup archive",
)
def backup(
    destination: str = Param(
        default="/backup",
        description="Backup destination path"
    ),
    compress: bool = Param(
        default=True,
        description="Compress the archive"
    ),
):
    """Create a backup with configurable options."""
    # Implementation here
    pass
```

### Ask Dialog System

Collect structured input using the `Ask()` function with typed dataclasses:

```python
from dataclasses import dataclass
from typing import Annotated
from contextipy import oneshot_script
from contextipy.questions import Ask, Question, Questions

@dataclass
class UserInfo(Questions):
    name: Annotated[str, Question.string(title="Your Name", required=True)]
    age: Annotated[int, Question.integer(title="Age", ge=0, le=120)]
    email: Annotated[str, Question.string(title="Email", required=False)]

@oneshot_script(
    script_id="collect_info",
    title="Collect User Info",
    description="Gather user information via dialog",
)
def collect_info():
    """Collect user information interactively."""
    info = Ask(UserInfo)
    
    if info is None:
        # User cancelled the dialog
        return []
    
    # Use validated, typed data
    return [Text(content=f"Hello, {info.name}! You are {info.age} years old.")]
```

See `examples/ask_dialog_demo.py` and `docs/ASK_DIALOG_IMPLEMENTATION.md` for comprehensive examples.

## Background Services

Services run continuously in the background and can be accessed by service scripts:

```python
from contextipy import service, service_script
from contextipy.actions import Text

@service(
    service_id="counter_service",
    title="Counter Service",
    description="Maintains a simple counter",
)
def counter_service():
    """Background service that maintains state."""
    class Counter:
        def __init__(self):
            self.value = 0
        
        def increment(self):
            self.value += 1
            return self.value
    
    return Counter()

@service_script(
    script_id="increment_counter",
    service_id="counter_service",
    title="Increment Counter",
    description="Increment the counter value",
)
def increment_counter(service_instance):
    """Increment and display the counter."""
    new_value = service_instance.increment()
    return [Text(content=f"Counter: {new_value}")]
```

Services are managed by `contextipy.execution.service_manager.ServiceManager` and automatically stopped on application exit.

See `examples/journal_service.py` for a complete example.

## Action System

Scripts interact with users through actions. Available action types:

```python
from contextipy.actions import (
    Open,      # Open a file with default application
    Text,      # Display text output
    Link,      # Open URL in browser
    Copy,      # Copy text to clipboard
    Notify,    # Show desktop notification
    Folder,    # Open folder in file explorer
    NoneAction # Explicit no-op with optional reason
)
```

Example:

```python
from pathlib import Path
from contextipy.actions import Open, Notify, Link

def my_script():
    return [
        Notify(title="Processing", message="Opening files..."),
        Open(target=Path("/path/to/file.txt")),
        Link(url="https://example.com"),
    ]
```

## UI Overview

The Contextipy tray application provides:

- **System Tray Icon**: Quick access to all features
- **Bilingual Menu**: Russian labels with English alternatives
  - Запущенные сервисы (Running Services)
  - Процессы (Processes)
  - Все скрипты и сервисы (All Scripts and Services)
  - Настройки (Settings)
  - Логи (Logs)
  - Выход (Exit)
- **Script Browser**: View and execute available scripts
- **Service Manager**: Start/stop background services
- **Logs Window**: Real-time execution logs
- **Settings**: Configure notifications and preferences

See `docs/ALL_SCRIPTS_WINDOW_QA.md` and `contextipy/ui/TRAY_README.md` for UI details.

## Building and Packaging

Build distributable executables for Windows and Linux:

```bash
# Build for current platform
python scripts/build.py --platform current --clean

# Build Windows executable
python scripts/build.py --platform windows

# Build Linux binary
python scripts/build.py --platform linux

# With smoke testing
python scripts/build.py --platform current --clean --smoke-test
```

The build system uses PyInstaller to create standalone executables with bundled dependencies.

See `docs/packaging.md` for comprehensive packaging documentation and deployment instructions.

## Development

### Tooling

- **Dependencies**: Managed by [Poetry](https://python-poetry.org/)
- **Linting & Formatting**: [ruff](https://github.com/astral-sh/ruff)
- **Type Checking**: [mypy](http://mypy-lang.org/)
- **Testing**: [pytest](https://docs.pytest.org/en/latest/)
- **Pre-commit**: Hooks enforce formatting and linting

### Running Tests

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_scanner_script_scanner.py

# Run with verbose output
pytest -v
```

### Pre-commit Hooks

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Project Structure

```
contextipy/
├── actions.py          # Action types (Open, Text, Notify, etc.)
├── core/               # Core decorators and types
│   ├── decorators.py   # @oneshot_script, @service, @service_script
│   ├── metadata.py     # Script metadata structures
│   ├── params.py       # Param() for script parameters
│   └── types.py        # Input markers (File, Folder, Image, etc.)
├── execution/          # Script and service execution
│   ├── script_runner.py    # Isolated script execution
│   └── service_manager.py  # Service lifecycle management
├── questions/          # Ask dialog system
│   ├── models.py       # Question definitions and Ask()
│   └── types.py        # Question types and validation
├── scanner/            # Script discovery and registry
│   ├── script_scanner.py        # Scan Python files for scripts
│   ├── registry.py              # Script metadata registry
│   └── dependency_installer.py  # Manage script dependencies
├── ui/                 # Qt-based UI components
│   ├── tray.py         # System tray application
│   └── windows/        # Dialog windows
├── config/             # Configuration management
└── logging/            # Execution logging

docs/                   # Documentation
examples/               # Example scripts
tests/                  # Test suite
scripts/                # Build and utility scripts
```

## Documentation

- [Quickstart Guide](docs/quickstart.md) - Get started quickly
- [Advanced Topics](docs/advanced_topics.md) - Services, packaging, and more
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions
- [Packaging Guide](docs/packaging.md) - Build and deploy executables
- [Dependency Installer](docs/dependency_installer.md) - Manage script dependencies
- [Ask Dialog](docs/ASK_DIALOG_IMPLEMENTATION.md) - Interactive input dialogs
- [Contributing](CONTRIBUTING.md) - Development guidelines

## Examples

See the `examples/` directory for complete, documented examples:

- `hello_world.py` - Basic oneshot script
- `file_processor.py` - File handling with dependencies
- `journal_service.py` - Background service with persistence
- `ask_dialog_demo.py` - Interactive dialog with validation

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code style guidelines
- Testing requirements
- Pull request process
- Development setup

---

**Note**: Contextipy is under active development. APIs may change between versions.
