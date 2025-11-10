# Build Scripts

This directory contains scripts for building distributable packages of Contextipy.

## Prerequisites

Before running these scripts, ensure PyInstaller is installed:
```bash
pip install pyinstaller
```

If using Poetry:
```bash
poetry run pip install pyinstaller
```

## Scripts

### `build.py`
Main build script using PyInstaller. Supports Windows and Linux builds with extensive configurability.

**Quick start:**
```bash
# Build for current platform
python scripts/build.py --platform current --clean --smoke-test

# Windows build
python scripts/build.py --platform windows --clean

# Linux build
python scripts/build.py --platform linux --clean
```

**Full usage:**
```
python scripts/build.py --help
```

### `build_nuitka.py`
Alternative Windows build script using Nuitka compiler. Produces native executables with potentially better performance.

**Quick start:**
```bash
python scripts/build_nuitka.py --clean
```

**Note:** Requires Microsoft Visual C++ Build Tools on Windows.

## Output Structure

After running a build, you'll find:

```
project/
├── dist/                      # Build artifacts
│   ├── Contextipy.exe        # Windows executable
│   └── contextipy            # Linux binary
├── build/                     # Temporary build files
└── specs/                     # PyInstaller spec files
    └── Contextipy.spec       # Generated spec for reproducibility
```

## CI/CD Integration

These scripts are integrated into GitHub Actions workflows (`.github/workflows/build.yml`) to automatically build and test packages on every push.

## Documentation

See `/docs/packaging.md` for comprehensive packaging instructions and `/docs/MANUAL_VERIFICATION.md` for manual testing procedures.
