# Advanced Topics

This guide covers advanced features including services, action returns, packaging, and registry management.

## Table of Contents

- [Service Lifecycle](#service-lifecycle)
- [Action Returns](#action-returns)
- [Packaging and Distribution](#packaging-and-distribution)
- [Script Parameters](#script-parameters)
- [Dependency Management](#dependency-management)
- [Registry and Metadata](#registry-and-metadata)

---

## Service Lifecycle

Services are long-running components that maintain state and are accessed by service scripts.

### Service Definition

Define a service with the `@service` decorator:

```python
from contextipy import service

@service(
    service_id="cache_service",
    title="Cache Service",
    description="In-memory cache for frequent operations",
    icon="💾",
)
def cache_service():
    """Initialize and return the service instance."""
    cache = {}
    
    class CacheManager:
        def set(self, key: str, value: str):
            cache[key] = value
        
        def get(self, key: str, default=None):
            return cache.get(key, default)
    
    return CacheManager()
```

### Service Scripts

Service scripts access the running service instance:

```python
from contextipy import service_script
from contextipy.actions import Text

@service_script(
    script_id="cache_get",
    service_id="cache_service",
    title="Get from Cache",
    description="Retrieve a cached value",
)
def cache_get(service_instance, key: str):
    """Retrieve and display a cached value."""
    value = service_instance.get(key, "Not found")
    return [Text(content=f"Cache[{key}] = {value}")]
```

### Lifecycle Management

Services are managed by `contextipy.execution.service_manager.ServiceManager`:

- **Startup**: Services are started when requested by a service script or configured to auto-start
- **Running**: Services maintain state and are accessible by all service scripts
- **Shutdown**: Services are gracefully stopped when the tray application exits

Example programmatic management:

```python
from contextipy.execution.service_manager import ServiceManager
from contextipy.config.persistence import ScriptRegistry

registry = ScriptRegistry()
manager = ServiceManager(registry=registry)

# Start a service
manager.start_service("cache_service")

# Check if running
is_running = manager.is_running("cache_service")

# Stop a service
manager.stop_service("cache_service")

# Stop all services on exit
manager.stop_all_services()
```

### Service Guidelines

- Services should handle initialization errors gracefully
- Services must be thread-safe if accessed concurrently
- Avoid blocking operations in service initialization
- Release resources (files, connections) in cleanup logic

---

## Action Returns

Scripts communicate results to users via action objects. All action types are immutable frozen dataclasses.

### Available Actions

```python
from contextipy.actions import (
    Open,       # Open file with default application
    Text,       # Display text output
    Link,       # Open URL in browser
    Copy,       # Copy text to clipboard
    Notify,     # Show desktop notification
    Folder,     # Open folder in file explorer
    NoneAction, # Explicit no-op
)
```

### Single vs Multiple Actions

Return a single action or a list:

```python
from contextipy import oneshot_script
from contextipy.actions import Text

@oneshot_script(script_id="single", title="Single", description="Single action")
def single_action():
    return Text(content="Single result")

@oneshot_script(script_id="multi", title="Multi", description="Multiple actions")
def multi_action():
    return [
        Text(content="First action"),
        Text(content="Second action"),
    ]
```

### Action Types and Usage

#### Open

Open files with their default application:

```python
from pathlib import Path
from contextipy.actions import Open

return Open(target=Path("/path/to/document.pdf"))
```

#### Text

Display text output:

```python
from contextipy.actions import Text

return Text(content="Script completed successfully!\nResults: 42")
```

#### Link

Open URLs in the default browser:

```python
from contextipy.actions import Link

return Link(url="https://example.com/search?q=python")
```

#### Copy

Copy text to the system clipboard:

```python
from contextipy.actions import Copy

return Copy(text="Copied this text to clipboard")
```

#### Notify

Show desktop notifications:

```python
from contextipy.actions import Notify

return Notify(title="Task Complete", message="Operation succeeded")
```

#### Folder

Open folders in the file explorer:

```python
from pathlib import Path
from contextipy.actions import Folder

return Folder(target=Path("/home/user/documents"))
```

#### NoneAction

Explicit no-op with optional reason:

```python
from contextipy.actions import NoneAction

return NoneAction(reason="Skipped due to configuration")
```

### Error Handling

Return actions that indicate errors:

```python
def my_script(file_path: str):
    try:
        # Process file
        return Text(content="Success")
    except FileNotFoundError:
        return Notify(title="Error", message=f"File not found: {file_path}")
    except Exception as e:
        return [
            Notify(title="Error", message="Processing failed"),
            Text(content=f"Exception: {str(e)}"),
        ]
```

---

## Packaging and Distribution

Build standalone executables for Windows and Linux using `scripts/build.py`.

### Basic Build

```bash
# Build for current platform
python scripts/build.py --platform current

# Build with clean state
python scripts/build.py --platform current --clean

# Build and run smoke test
python scripts/build.py --platform current --clean --smoke-test
```

### Platform-Specific Builds

```bash
# Windows executable
python scripts/build.py --platform windows

# Linux binary
python scripts/build.py --platform linux

# Both (requires matching OS)
python scripts/build.py --all
```

### Build Options

| Option | Description |
| ------ | ----------- |
| `--platform` | Target platform: `windows`, `linux`, `current` |
| `--all` | Build for all platforms (requires native OS) |
| `--output` | Output directory (default: `dist/`) |
| `--clean` | Clean build directories before building |
| `--smoke-test` | Run basic smoke test after building |

### Bundling Script Dependencies

Scripts with declared dependencies have their requirements installed before packaging:

```python
"""Script with dependencies.

Requirements:
    requests>=2.31.0
    beautifulsoup4>=4.12.0
"""
```

The build system:
1. Scans scripts for requirements
2. Installs dependencies in isolated environments
3. Bundles packages with the executable

See [packaging.md](./packaging.md) for comprehensive packaging documentation.

### Distribution

Distribute the built executable:

- **Windows**: `dist/contextipy-tray.exe`
- **Linux**: `dist/contextipy-tray`

Include a launcher script or installer for users who need configuration.

---

## Script Parameters

Scripts accept configurable parameters with `Param()`:

```python
from contextipy import Param, oneshot_script

@oneshot_script(
    script_id="backup",
    title="Backup Files",
    description="Create file backups",
)
def backup(
    destination: str = Param(
        default="/backup",
        description="Backup destination directory"
    ),
    compress: bool = Param(
        default=True,
        description="Compress the archive"
    ),
    max_size_mb: int = Param(
        default=100,
        description="Maximum backup size in MB"
    ),
):
    """Create a backup with configurable parameters."""
    # Implementation omitted
```

### Parameter Types

Parameters support standard Python types:

- `str`, `int`, `float`, `bool`
- `Path` from `pathlib`
- `list`, `dict` (serialisable types)

### Default Values

Parameters without defaults are required. The UI prompts for missing values.

---

## Dependency Management

Contextipy automates dependency installation using docstring declarations.

### Docstring Requirements Format

Two formats are supported:

**Format 1**: Dedicated `Requirements:` section

```python
"""
Script description.

Requirements:
    requests>=2.31.0
    beautifulsoup4>=4.12.0
    lxml  # HTML/XML parsing
"""
```

**Format 2**: Markdown code fence

```python
"""
Script description.

```requirements
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml
```
"""
```

### Parsing Rules

- One requirement per line
- Comments with `#` are ignored
- List prefixes (`-`, `*`) are stripped
- Version specifiers (`>=`, `==`, `~=`) are preserved
- Duplicates are removed

### Venv Strategies

Two strategies are available:

**Per-Script Venv** (default):
- Each script gets its own isolated environment
- Prevents dependency conflicts
- More disk space usage

**Shared Venv**:
- Single environment for all scripts
- Shared dependencies reduce disk usage
- Risk of version conflicts

Configure via `contextipy.scanner.dependency_installer`:

```python
from contextipy.scanner import (
    DependencyInstaller,
    PerScriptVenvStrategy,
    SharedVenvStrategy,
)

# Per-script
installer = DependencyInstaller(strategy=PerScriptVenvStrategy())

# Shared
installer = DependencyInstaller(strategy=SharedVenvStrategy())
```

### Caching

Installed dependencies are cached based on requirements hash. Contextipy skips reinstallation if:

1. Requirements haven't changed
2. Venv exists and is valid
3. Cache marker is present

To force reinstallation, delete the venv directory or cache marker.

See [dependency_installer.md](./dependency_installer.md) for full documentation.

---

## Registry and Metadata

The script registry tracks discovered scripts, manages settings, and notifies listeners of changes.

### ScriptScanner

Scan directories for decorated scripts:

```python
from pathlib import Path
from contextipy.scanner import ScriptScanner

scanner = ScriptScanner(Path("~/.contextipy/scripts").expanduser())
result = scanner.scan()

for script in result.scripts:
    print(f"{script.script_id}: {script.title}")

for error in result.errors:
    print(f"Error in {error.path}: {error.message}")
```

### ScriptMetadataRegistry

The registry stores metadata and settings:

```python
from contextipy.scanner import ScriptMetadataRegistry
from contextipy.config.persistence import ScriptRegistry

storage = ScriptRegistry(db_path)
registry = ScriptMetadataRegistry(storage=storage, scanner=scanner)

# Initial scan
registry.rescan()

# Enable/disable scripts
registry.set_enabled("my_script", False)

# Mark scripts for startup
registry.set_startup("my_script", True)

# Query by category
scripts = registry.query_by_category("utilities")

# Query by group
scripts = registry.query_by_group(("text", "converters"))
```

### Change Callbacks

Register callbacks for registry changes:

```python
def on_registry_change():
    print("Registry updated")

registry.add_change_callback(on_registry_change)
```

### Persistence

Settings persist to SQLite via `contextipy.config.persistence.ScriptRegistry`. Changes are saved automatically.

---

## Next Steps

- Review [troubleshooting.md](./troubleshooting.md) for common issues
- Explore [examples/](../examples/README.md) for complete code
- Consult API references in the codebase

Happy scripting! 🚀
