# Manual Verification Guide

This guide documents the manual verification steps required to validate that the packaged Contextipy application launches correctly and displays in the system tray.

## Overview

After the CI build completes and produces the executable artifacts, QA should perform manual testing on target machines to ensure:
1. The executable launches without errors
2. The application appears in the system tray
3. Basic tray functionality is operational

## Windows Manual Verification

### Prerequisites
- Windows 10 or later
- Access to the built `Contextipy.exe` from CI artifacts

### Steps

1. **Download the Artifact**
   - Go to the GitHub Actions run that completed successfully
   - Download the `contextipy-windows` artifact (contains `Contextipy.exe`)
   - Extract to a test directory (e.g., `C:\Test\Contextipy\`)

2. **Launch the Executable**
   ```
   Double-click Contextipy.exe or run from PowerShell:
   .\Contextipy.exe
   ```

3. **Verify Launch**
   - ✅ Application starts without error dialogs
   - ✅ No console window appears (should be windowed mode)
   - ✅ Process appears in Task Manager

4. **Check System Tray**
   - Look for the Contextipy icon in the system tray (bottom-right near clock)
   - If hidden, expand the overflow area (^) to see all tray icons
   - ✅ Icon is visible

5. **Test Tray Icon Interaction**
   - Right-click the tray icon
   - ✅ Context menu appears (once implemented)
   - Left-click the tray icon
   - ✅ Main window or action occurs (once implemented)

6. **Test Exit**
   - Select "Exit" from tray menu or close the application
   - ✅ Application closes cleanly
   - ✅ Process terminates in Task Manager

### Expected Results

| Check | Expected Result |
|-------|----------------|
| Launch | Starts without errors |
| Console | No console window visible |
| Tray Icon | Visible in system tray |
| Icon Quality | Icon renders clearly |
| Interaction | Responds to clicks |
| Exit | Closes cleanly |

### Known Issues / Limitations

- During early development phases, the tray icon may be a placeholder
- Actual menu functionality depends on implementation status
- First launch may take longer due to unpacking (PyInstaller)

## Linux Manual Verification

### Prerequisites
- Ubuntu 22.04+, Fedora 38+, or similar modern Linux distribution
- Desktop environment with system tray support (GNOME Shell, KDE Plasma, XFCE, etc.)
- Access to the built `contextipy` binary from CI artifacts

### Steps

1. **Download the Artifact**
   ```bash
   # Download from GitHub Actions artifacts
   # Extract to test directory
   cd ~/test
   unzip contextipy-linux.zip
   chmod +x contextipy
   ```

2. **Launch the Binary**
   ```bash
   ./contextipy
   ```

3. **Verify Launch**
   - ✅ Application starts without errors
   - ✅ No error dialogs appear
   - ✅ Process appears in `ps aux | grep contextipy`

4. **Check System Tray**
   - Look for Contextipy icon in the system tray
   - Location depends on DE:
     - GNOME: Top bar (may require extensions like AppIndicator)
     - KDE: Bottom-right panel
     - XFCE: Top or bottom panel
   - ✅ Icon is visible

5. **Test Tray Icon Interaction**
   - Right-click the tray icon
   - ✅ Context menu appears
   - Left-click the tray icon
   - ✅ Expected action occurs

6. **Test Exit**
   ```bash
   # Via tray menu or kill process
   killall contextipy
   ```
   - ✅ Application terminates cleanly

### Expected Results

| Check | Expected Result |
|-------|----------------|
| Launch | Starts without errors |
| Dependencies | No missing library errors |
| Tray Icon | Visible in system tray |
| Icon Quality | Icon renders correctly |
| Interaction | Responds to clicks |
| Exit | Closes cleanly |

### Troubleshooting

**Icon not appearing:**
- Ensure desktop environment supports tray icons
- Install tray extensions if using GNOME:
  ```bash
  sudo apt install gnome-shell-extension-appindicator
  ```
- Restart desktop session

**Missing libraries:**
```bash
ldd ./contextipy
# Check for "not found" entries
```

## Smoke Test Results

The automated smoke test (`--smoke-test` flag) performs basic launch validation but does **not** verify tray functionality. Manual testing is essential to confirm:
- Tray icon appearance
- Icon visual quality
- User interaction
- Menu functionality

## Reporting Issues

When reporting issues, please include:
1. Operating system and version
2. Desktop environment (Linux only)
3. Build artifact date/version
4. Error messages or screenshots
5. Steps to reproduce

## Acceptance Criteria Summary

### Windows Build
- ✅ Build completes in CI without errors
- ✅ `Contextipy.exe` is produced and downloadable
- ✅ Smoke test passes (basic launch)
- ✅ Manual verification: executable launches to tray

### Linux Build
- ✅ Build completes in CI without errors
- ✅ `contextipy` binary is produced and downloadable
- ✅ Smoke test passes (basic launch)
- ✅ Manual verification: binary launches to tray (on supported DE)
