# Dependency Installer

The dependency installer provides automatic dependency management for Contextipy scripts. When scripts declare their dependencies in their docstrings, the system automatically installs them using pip with caching and retry logic.

## Features

- **Automatic Dependency Detection**: Parses requirements from script docstrings
- **Installation Caching**: Avoids redundant installations when dependencies haven't changed
- **Retry Logic**: Automatically retries failed installations with exponential backoff
- **Virtual Environment Support**: Supports both shared and per-script virtual environments
- **Logging**: Comprehensive logging of installation attempts and outcomes
- **Registry Integration**: Seamlessly integrates with the script registry

## Declaring Dependencies

Dependencies can be declared in script docstrings using two formats:

### Format 1: Requirements Section

```python
from contextipy import oneshot_script

@oneshot_script(
    script_id="example",
    title="Example Script",
    description="A script with dependencies",
)
def my_script() -> str:
    """Script with external dependencies.

    Requirements:
        requests>=2.28.0
        pandas>=1.5.0
        numpy>=1.20.0

    The script does something useful with these libraries.
    """
    import requests
    import pandas as pd
    return "success"
```

### Format 2: Fenced Code Block

```python
from contextipy import oneshot_script

@oneshot_script(
    script_id="example",
    title="Example Script",
    description="A script with dependencies",
)
def my_script() -> str:
    """Script with external dependencies.

    ```requirements
    requests>=2.28.0
    pandas>=1.5.0
    ```

    The script does something useful.
    """
    import requests
    return "success"
```

### Requirements Format

- Each requirement should be on its own line
- Follow standard pip requirement format (e.g., `package>=version`)
- Inline comments are supported: `requests>=2.28.0  # HTTP library`
- Bullet points are supported: `- requests>=2.28.0` or `* requests>=2.28.0`
- Empty lines and comments (`# comment only`) are ignored
- Duplicate requirements are automatically removed

## Virtual Environment Strategies

The dependency installer supports two virtual environment strategies:

### Shared Virtual Environment

A single virtual environment is used for all scripts. This is memory-efficient but may lead to dependency conflicts.

```python
from pathlib import Path
from contextipy.scanner import (
    SharedVenvStrategy,
    DependencyInstaller,
)

venv_path = Path.home() / ".contextipy" / "shared_venv"
strategy = SharedVenvStrategy(venv_path)
installer = DependencyInstaller(strategy)
```

### Per-Script Virtual Environment

Each script gets its own isolated virtual environment. This prevents dependency conflicts but uses more disk space.

```python
from pathlib import Path
from contextipy.scanner import (
    PerScriptVenvStrategy,
    DependencyInstaller,
)

venv_root = Path.home() / ".contextipy" / "venvs"
strategy = PerScriptVenvStrategy(venv_root)
installer = DependencyInstaller(strategy)
```

## Configuration

The installer can be configured with custom settings:

```python
from contextipy.scanner import (
    DependencyInstaller,
    InstallConfig,
    SharedVenvStrategy,
)

config = InstallConfig(
    max_retries=5,              # Number of retry attempts
    retry_delay=2.0,            # Initial retry delay in seconds
    backoff_multiplier=2.0,     # Exponential backoff multiplier
    timeout=600.0,              # Installation timeout in seconds
    pip_args=("--no-cache-dir",)  # Additional pip arguments
)

strategy = SharedVenvStrategy(Path("/path/to/venv"))
installer = DependencyInstaller(strategy, config=config)
```

## Integration with Registry

To enable automatic dependency installation during script scanning:

```python
from contextipy.scanner import (
    ScriptMetadataRegistry,
    ScriptScanner,
    DependencyInstaller,
    SharedVenvStrategy,
)
from contextipy.config.persistence import ScriptRegistry

# Create components
storage = ScriptRegistry()
scanner = ScriptScanner(Path("/path/to/scripts"))
strategy = SharedVenvStrategy(Path("/path/to/venv"))
installer = DependencyInstaller(strategy)

# Create registry with installer
registry = ScriptMetadataRegistry(
    storage=storage,
    scanner=scanner,
    dependency_installer=installer,
)

# Rescan will now automatically install dependencies
result = registry.rescan()
```

When a script is newly discovered or updated (file hash changes), the registry will:
1. Parse the script's docstring for requirements
2. Install the requirements using the configured installer
3. Cache the installation to avoid redundant installs
4. Log the installation outcome
5. Continue with registration even if installation fails

## Cache Management

The installer maintains a cache to avoid redundant installations:

```python
# Clear cache for a specific script
installer.clear_cache("script_id")

# Clear all cache
installer.clear_cache()
```

The cache is automatically invalidated when:
- Requirements change (different hash)
- Cache is manually cleared

## Installation Results

All installation attempts return an `InstallResult`:

```python
from contextipy.scanner import InstallStatus

result = installer.install_requirements("script_id", ("requests>=2.28.0",))

# Check status
if result.successful():
    print(f"Installation successful: {result.status.value}")
else:
    print(f"Installation failed: {result.error_message}")

# Access details
print(f"Status: {result.status}")  # SUCCESS, CACHED, FAILED, or SKIPPED
print(f"Requirements: {result.requirements}")
print(f"Stdout: {result.stdout}")
print(f"Stderr: {result.stderr}")
```

### Status Values

- `SUCCESS`: Dependencies were successfully installed
- `CACHED`: Dependencies were already installed (cache hit)
- `SKIPPED`: No dependencies to install
- `FAILED`: Installation failed after all retries

## Logging

The installer uses Python's logging module. Configure logging to see installation details:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("contextipy.scanner.dependency_installer")
logger.setLevel(logging.DEBUG)
```

Log levels:
- **DEBUG**: Cache hits, pip commands
- **INFO**: Successful installations, virtual environment creation
- **WARNING**: Retry attempts, cache write failures
- **ERROR**: Installation failures, virtual environment creation errors

## Best Practices

1. **Pin Versions**: Use specific version constraints (e.g., `requests>=2.28.0,<3.0.0`)
2. **Minimal Dependencies**: Only declare essential dependencies
3. **Test Locally**: Test scripts with dependencies in a clean environment
4. **Handle Import Errors**: Scripts should handle missing dependencies gracefully
5. **Clear Cache**: Clear cache after major dependency updates
6. **Monitor Logs**: Review logs for installation failures or conflicts

## Error Handling

The installer is designed to be resilient:

- **Retry Logic**: Failed installations are automatically retried with exponential backoff
- **Graceful Degradation**: Registry registration continues even if installation fails
- **Comprehensive Logging**: All errors are logged with context
- **Timeout Protection**: Long-running installations are automatically terminated

## Examples

### Example 1: Simple Script with Dependencies

```python
from contextipy import oneshot_script

@oneshot_script(
    script_id="fetch_data",
    title="Fetch Data",
    description="Fetches data from an API",
)
def fetch_data(url: str) -> dict:
    """Fetch JSON data from a URL.

    Requirements:
        requests>=2.28.0

    Args:
        url: The URL to fetch data from

    Returns:
        JSON response as a dictionary
    """
    import requests
    response = requests.get(url)
    return response.json()
```

### Example 2: Data Analysis Script

```python
from contextipy import oneshot_script

@oneshot_script(
    script_id="analyze_csv",
    title="Analyze CSV",
    description="Analyzes CSV data",
    accepts=("File",),
)
def analyze_csv(file_path: str) -> str:
    """Analyze a CSV file and return statistics.

    ```requirements
    pandas>=1.5.0
    numpy>=1.20.0
    matplotlib>=3.5.0
    ```

    Args:
        file_path: Path to the CSV file

    Returns:
        Analysis summary
    """
    import pandas as pd
    import numpy as np

    df = pd.read_csv(file_path)
    return f"Rows: {len(df)}, Columns: {len(df.columns)}"
```

### Example 3: Custom Configuration

```python
from pathlib import Path
from contextipy.scanner import (
    DependencyInstaller,
    InstallConfig,
    PerScriptVenvStrategy,
)

# Configure for production use
config = InstallConfig(
    max_retries=5,
    retry_delay=1.0,
    backoff_multiplier=2.0,
    timeout=300.0,
    pip_args=("--quiet", "--no-warn-script-location"),
)

# Use per-script environments for isolation
strategy = PerScriptVenvStrategy(Path.home() / ".contextipy" / "script_venvs")

# Create installer
installer = DependencyInstaller(
    strategy=strategy,
    cache_dir=Path.home() / ".contextipy" / "dep_cache",
    config=config,
)

# Use with registry
# ... (see Integration with Registry section)
```
