# Contributing to Contextipy

Thank you for your interest in contributing to Contextipy! This document outlines the development workflow
and guidelines for working on the project.

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd contextipy
   ```

2. **Install Poetry** (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. **Install dependencies:**
   ```bash
   poetry install
   ```

4. **Activate the virtual environment:**
   ```bash
   poetry shell
   ```

5. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

## Code Quality

This project uses several tools to maintain code quality:

- **Ruff:** Fast Python linter and formatter (replaces flake8, isort, and more)
- **Mypy:** Static type checker
- **Pytest:** Testing framework with coverage

### Testing Strategy

Our automated test harness is built on top of `pytest` with shared fixtures located in
`tests/conftest.py`. Key fixtures include:

- `temp_script_dir` – provides an isolated directory for creating sample scripts.
- `isolated_registry` – resets the global decorator registry between tests.
- `mock_subprocess` / `mock_subprocess_popen` – isolates subprocess execution.
- `mock_platform_*` – simulate Windows, Linux, or macOS specific behaviour.
- `mock_home_dir` – redirects configuration persistence to a temporary location.

Tests default to running in headless mode by exporting `QT_QPA_PLATFORM=offscreen`. GUI
or platform-specific tests are marked with `@pytest.mark.ui`, `@pytest.mark.windows_only`,
`@pytest.mark.linux_only`, or `@pytest.mark.macos_only` and are automatically skipped on
unsupported platforms.

Coverage reports (terminal, HTML, XML) are generated automatically via the pytest
configuration in `pyproject.toml`. HTML reports are written to `htmlcov/` and the XML
artifact is available for CI uploads.

### Running Checks Locally

```bash
# Run all pre-commit hooks manually
pre-commit run --all-files

# Run tests with coverage
pytest

# Limit test run to a specific module or mark
pytest tests/test_harness_execution.py -m "not slow"

# Run type checking
mypy contextipy

# Run linting
ruff check contextipy

# Run formatting
ruff format contextipy
```

When working on features touching subprocess execution or platform-specific code, prefer
unit tests that rely on the shared fixtures so they remain deterministic and portable.

## Code Style

- Follow PEP 8 conventions
- Use type hints for all function signatures
- Write docstrings for all public modules, classes, and functions
- Keep functions focused and testable
- Maintain test coverage for new features

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes and ensure all checks pass
3. Update documentation as needed
4. Submit a pull request with a clear description of the changes

## Questions?

Feel free to open an issue for any questions or concerns about contributing.
