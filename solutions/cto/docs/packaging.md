# Packaging and Deployment Guide

This document covers the process of building distributable packages for Contextipy on Windows and Linux, including required dependencies, automated scripts, and manual verification steps.

## Prerequisites

### Common Requirements
- Python 3.10+
- Poetry (for dependency management)
- PyInstaller (`pip install pyinstaller` inside your virtual environment)
- Git (for cloning the repo)

### OS-Specific Requirements

#### Windows
- Windows 10 or later
- Optional: Microsoft Visual C++ Build Tools (for Nuitka builds)
- PyInstaller or Nuitka (PyInstaller is default)
- PowerShell or Command Prompt

#### Linux
- Ubuntu 22.04+, Fedora 38+, or similar modern distribution
- GCC and build-essential (or equivalent) for PyInstaller
- Optional: `systemd --user` support for autostart
- Desktop environment that supports tray icons

## Automated Builds (`scripts/build.py`)

This script automates packaging for both Windows and Linux. Usage examples:

```bash
# Build Windows executable
python scripts/build.py --platform windows

# Build Linux binary
python scripts/build.py --platform linux

# Build for current OS with clean initial state and smoke test
python scripts/build.py --platform current --clean --smoke-test

# Build for all platforms (on matching OS)
python scripts/build.py --all

# Custom output directory
python scripts/build.py --platform windows --output ./releases
```

### Script Features
- Bundles resources (icons, `.desktop` templates)
- Runs basic smoke tests with `--smoke-test` flag
- Supports clean builds via `--clean`
- Configurable output directory via `--output`
- Collects hidden imports for PySide6 and platform-specific modules
- Generates `.spec` files in `specs/` directory for reproducibility

### CLI Options

| Option | Description |
| ------ | ----------- |
| `--platform <windows\|linux\|current>` | Target platform to build for |
| `--all` | Build for all platforms (requires matching OS) |
| `--output <path>` | Output directory for artifacts (default: `dist/`) |
| `--clean` | Clean build directories before building |
| `--smoke-test` | Run smoke test after building |

### Alternative: Nuitka Build (Windows)

For better performance or smaller executables, use Nuitka:

```bash
python scripts/build_nuitka.py --clean
```

Note: Nuitka requires Microsoft Visual C++ Build Tools on Windows.

## Windows Packaging

1. Run:
   ```bash
   python scripts/build.py --platform windows --clean
   ```

2. Output: `dist/Contextipy.exe`

3. Manual verification (see [MANUAL_VERIFICATION.md](./MANUAL_VERIFICATION.md)):
   - Launch the `.exe` to ensure it runs without errors
   - Confirm tray icon appears (depends on actual tray implementation)

## Linux Packaging

1. Run:
   ```bash
   python scripts/build.py --platform linux --clean
   ```

2. Output: `dist/contextipy`

3. Manual verification (see [MANUAL_VERIFICATION.md](./MANUAL_VERIFICATION.md)):
   - Execute `./dist/contextipy`
   - Check for tray icon behavior

4. Create `.desktop` file with `contextipy/ui/resources/contextipy.desktop.template`
   - Replace `{INSTALL_PATH}` with actual install path

### Optional systemd user service

Create `~/.config/systemd/user/contextipy.service`:
```ini
[Unit]
Description=Contextipy Tray Service
After=network.target

[Service]
ExecStart=/path/to/dist/contextipy
Restart=on-failure

[Install]
WantedBy=default.target
```

Enable:
```bash
systemctl --user enable contextipy.service
systemctl --user start contextipy.service
```

## CI Considerations

- Ensure Windows runners have PyInstaller installed (script handles auto-install)
- Smoke tests run via `--smoke-test` to validate the build
- Documented manual verification steps allow QA to confirm tray functionality

## Troubleshooting

- Missing resources: ensure `contextipy/ui/resources` is included
- Dependency issues: run `poetry install` to sync environment
- PyInstaller failures: rerun with `--clean` and check logs in `build/`
