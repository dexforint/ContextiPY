# Contextipy Quickstart Guide

Welcome to Contextipy! This guide walks you through installing the application, running the tray UI, and authoring your first script.

## Prerequisites

- Python 3.10 or newer
- git (optional, for cloning the repository)
- Virtual environment (recommended)

## Installation

```bash
# Clone the repository (optional if you already have the source)
git clone https://github.com/your-org/contextipy.git
cd contextipy

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install Contextipy in editable mode
pip install -e .
```

If you prefer Poetry, install dependencies with:

```bash
poetry install
poetry shell
```

## Running the Tray Application

After installation, start the system tray application:

```bash
contextipy-tray
```

The tray icon appears near your system clock. Right-click the icon to access the bilingual menu:

- **Запущенные сервисы** (Running Services)
- **Процессы** (Processes)
- **Все скрипты и сервисы** (All Scripts and Services)
- **Настройки** (Settings)
- **Логи** (Logs)
- **Выход** (Exit)

## Creating Your First Script

Scripts are discovered automatically from the user scripts directory. By default this is `~/.contextipy/scripts/`, but you can customise it in settings.

Create a new script file, for example `~/.contextipy/scripts/hello_world.py`:

```python
"""Simple hello world script."""

from contextipy import oneshot_script
from contextipy.actions import Notify, Text

@oneshot_script(
    script_id="hello_world",
    title="Hello World",
    description="Display a greeting",
)
def hello_world():
    """Return greeting actions."""
    return [
        Notify(title="Hello!", message="Welcome to Contextipy"),
        Text(content="This is your first script."),
    ]
```

Save the file. Within a few seconds the watcher notices the change and your script appears in the tray under "All Scripts and Services".

## Declaring Dependencies

Contextipy installs dependencies automatically when declared in a docstring:

```python
"""Convert images to grayscale.

Requirements:
    Pillow>=10.0.0
"""

from contextipy import Image, oneshot_script
from PIL import Image as PILImage

@oneshot_script(
    script_id="grayscale",
    title="Grayscale Converter",
    description="Convert selected images to grayscale",
    accepts=[Image],
)
def grayscale(selected_paths: list):
    """Convert selected images."""
    # Implementation omitted
```

When you launch the script, Contextipy ensures `Pillow` is installed in the managed environment.

## Collecting Input with Ask()

Use the Ask dialog to collect structured input:

```python
from dataclasses import dataclass
from typing import Annotated

from contextipy import oneshot_script
from contextipy.actions import Text
from contextipy.questions import Ask, Question, Questions

@dataclass
class UserDetails(Questions):
    name: Annotated[str, Question.string(title="Your Name", required=True)]
    age: Annotated[int, Question.integer(title="Age", ge=0)]

@oneshot_script(
    script_id="ask_demo",
    title="Ask Demo",
    description="Collect user details",
)
def ask_demo():
    response = Ask(UserDetails)
    if response is None:
        return []
    return [Text(content=f"Hello, {response.name}! You are {response.age} years old.")]
```

## Background Services

Services run persistently and provide shared state:

```python
from contextipy import service, service_script

@service(
    service_id="note_service",
    title="Note Service",
    description="Collect quick notes",
)
def note_service():
    return []

@service_script(
    script_id="add_note",
    service_id="note_service",
    title="Add Note",
    description="Store a note",
)
def add_note(service_instance, text: str):
    service_instance.append(text)
    return []
```

See `examples/journal_service.py` for a complete, documented example.

## Packaging the Application

To build platform-specific bundles, use the build script:

```bash
python scripts/build.py --platform current --clean
```

Refer to the [Advanced Topics](./advanced_topics.md#packaging) and [Packaging Guide](./packaging.md) for details.

## Next Steps

- Browse the [examples directory](../examples/README.md)
- Explore advanced features in [docs/advanced_topics.md](./advanced_topics.md)
- Troubleshoot issues with [docs/troubleshooting.md](./troubleshooting.md)

Happy scripting! 🎉
