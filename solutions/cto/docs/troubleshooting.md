# Troubleshooting Guide

This guide helps diagnose and resolve common issues encountered while using Contextipy.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Tray Application Problems](#tray-application-problems)
- [Script Discovery & Execution](#script-discovery--execution)
- [Dependency Installation](#dependency-installation)
- [Ask Dialog Issues](#ask-dialog-issues)
- [Service Lifecycle](#service-lifecycle)
- [UI & Bilingual Labels](#ui--bilingual-labels)
- [Logging & Debugging](#logging--debugging)

---

## Installation Issues

### `pip install -e .` fails

- Ensure you are using Python 3.10+
- Upgrade pip: `python -m pip install --upgrade pip`
- Check that PySide6 build prerequisites exist for your platform
- On Linux, install `python3-dev`, `libxcb`, and other Qt dependencies

### Virtual environment activation errors

- On Windows use `venv\Scripts\activate`
- On macOS/Linux use `source venv/bin/activate`
- If shell reports execution policy errors on Windows, run PowerShell as Administrator: `Set-ExecutionPolicy RemoteSigned`

---

## Tray Application Problems

### Tray icon not visible

- Ensure the application is running: `contextipy-tray`
- Some desktop environments hide inactive icons; check the overflow menu
- On Linux, install a status notifier extension (e.g., for GNOME) if necessary

### Application crashes on startup

- Verify PySide6 installed correctly
- Run with logging to inspect errors:
  ```bash
  contextipy-tray --log-level DEBUG
  ```

- Check `~/.contextipy/logs/contextipy.log` for stack traces

---

## Script Discovery & Execution

### Scripts not appearing in menu

- Confirm scripts reside in the scripts directory (`~/.contextipy/scripts/` by default)
- Ensure files have a `.py` extension
- Verify decorated functions use supported decorators: `@oneshot_script`, `@service`, `@service_script`
- Check for syntax errors in script (`python -m compileall path/to/script.py`)
- Review the registry logs in `~/.contextipy/logs/registry.log`

### Script returns unexpected results

- Ensure returns conform to supported action types (`contextipy.actions`)
- For single action return, returning the action instance is sufficient; lists are also accepted
- Use `Text` or `Notify` actions to expose debug information

### Registry scanner errors

- Run `python -m contextipy.scanner.script_scanner /path/to/scripts` for diagnostics
- Review error messages referencing missing decorator arguments

---

## Dependency Installation

### Dependencies not installing

- Confirm docstring uses supported formats (`Requirements:` section or ```requirements``` fence)
- Ensure requirement lines contain valid package names and version specifiers
- Check `~/.contextipy/venvs/<script_id>/install.log` for pip output
- Delete the script's venv directory to force reinstall

### Installation times out

- Increase timeout via `InstallConfig(timeout=600)` if running large installs
- Check network connectivity and pip mirrors
- Avoid installing large build-from-source packages when possible

---

## Ask Dialog Issues

### Dialog not displaying

- Confirm `Ask()` receives a subclass of `Questions`
- Ensure dataclass fields use `typing.Annotated` with `Question.*` metadata
- Check logs for validation errors triggered during schema generation

### User input rejected unexpectedly

- Validate constraints (`ge`, `le`, `regex`) match expected values
- Ensure defaults are serialisable and pass validation

---

## Service Lifecycle

### Service not starting

- Verify `@service` decorator includes required arguments (`service_id`, `title`, `description`)
- Check logs for initialization errors
- Ensure service script references correct `service_id`

### Service remains running after exit

- Services should shut down via `ServiceManager.stop_all_services()` on application exit
- Confirm `contextipy-tray` closed cleanly (no lingering processes)

### Service instance missing in script

- Service scripts must accept `service_instance` parameter
- Verify the service returns an object; avoid returning `None`

---

## UI & Bilingual Labels

### Menu labels appear only in Russian

- Bilingual labels are provided as Russian text with English references in documentation
- Custom builds can modify labels in `contextipy/ui/tray.py`
- Ensure fonts supporting Cyrillic characters are installed

### UI scaling issues

- Configure Qt scaling environment variables:
  ```bash
  export QT_SCALE_FACTOR=1.2
  contextipy-tray
  ```
- On Windows, enable high DPI support via display settings

---

## Logging & Debugging

### Enable verbose logging

- Start the tray application with debug logging:
  ```bash
  contextipy-tray --log-level DEBUG
  ```
- Log files reside in `~/.contextipy/logs/`

### Capturing script output

- Use the Logs window (Логи) accessible from the tray menu
- Programmatically access logs via `contextipy.logging.logger.ExecutionLogger`

### Inline debugging in scripts

- Use `print()` statements; output captured in logs
- Return diagnostic `Text` actions for visibility

---

## Getting Help

- Review [quickstart guide](./quickstart.md) for setup basics
- Explore [advanced topics](./advanced_topics.md) for in-depth coverage
- Check issue tracker or community channels for support

Happy automating!
