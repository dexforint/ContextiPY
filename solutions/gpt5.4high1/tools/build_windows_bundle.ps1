[CmdletBinding()]
param(
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location $projectRoot

$distRoot = Join-Path $projectRoot "dist\pcontext-windows"
$pyInstallerWork = Join-Path $projectRoot "build\pyinstaller"

if ($Clean) {
    if (Test-Path -LiteralPath $distRoot) {
        Remove-Item -LiteralPath $distRoot -Recurse -Force
    }

    if (Test-Path -LiteralPath $pyInstallerWork) {
        Remove-Item -LiteralPath $pyInstallerWork -Recurse -Force
    }
}

$null = New-Item -ItemType Directory -Path $distRoot -Force
$null = New-Item -ItemType Directory -Path $pyInstallerWork -Force

Write-Host "Building Rust launcher..."
Push-Location (Join-Path $projectRoot "native\windows-shell")
cargo build --release --bin pcontext-launcher
Pop-Location

$launcherExe = Join-Path $projectRoot "native\windows-shell\target\release\pcontext-launcher.exe"
if (-not (Test-Path -LiteralPath $launcherExe)) {
    throw "Launcher exe was not found after cargo build: $launcherExe"
}

$iconPath = Join-Path $HOME ".pcontext\icons\pcontext.ico"
$pyInstallerArgs = @(
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--name", "pcontext-gui",
    "--distpath", $distRoot,
    "--workpath", $pyInstallerWork,
    "--specpath", $pyInstallerWork,
    "--paths", (Join-Path $projectRoot "src"),
    (Join-Path $projectRoot "src\pcontext\windows_gui_entry.py")
)

if (Test-Path -LiteralPath $iconPath) {
    $pyInstallerArgs += @("--icon", $iconPath)
}

Write-Host "Building pcontext-gui.exe with PyInstaller..."
uv run pyinstaller @pyInstallerArgs

$guiExe = Join-Path $distRoot "pcontext-gui.exe"
if (-not (Test-Path -LiteralPath $guiExe)) {
    throw "GUI exe was not found after PyInstaller build: $guiExe"
}

Copy-Item -LiteralPath $launcherExe -Destination (Join-Path $distRoot "pcontext-launcher.exe") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "tools\windows_install_bundle.ps1") -Destination (Join-Path $distRoot "windows_install_bundle.ps1") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "tools\windows_uninstall_bundle.ps1") -Destination (Join-Path $distRoot "windows_uninstall_bundle.ps1") -Force

$bundleSrcDir = Join-Path $distRoot "src"
if (Test-Path -LiteralPath $bundleSrcDir) {
    Remove-Item -LiteralPath $bundleSrcDir -Recurse -Force
}
Copy-Item -LiteralPath (Join-Path $projectRoot "src") -Destination $bundleSrcDir -Recurse -Force

$readmePath = Join-Path $distRoot "README.txt"
@"
PContext Windows bundle

Files:
- pcontext-gui.exe
- pcontext-launcher.exe
- src\
- windows_install_bundle.ps1
- windows_uninstall_bundle.ps1

Install:
powershell -ExecutionPolicy Bypass -File .\windows_install_bundle.ps1 -RestartExplorer

Install with autostart:
powershell -ExecutionPolicy Bypass -File .\windows_install_bundle.ps1 -EnableAutostart -RestartExplorer

Uninstall:
powershell -ExecutionPolicy Bypass -File .\windows_uninstall_bundle.ps1 -RestartExplorer
"@ | Set-Content -LiteralPath $readmePath -Encoding UTF8

Write-Host "Build completed."
Write-Host "GUI: $guiExe"
Write-Host "Launcher: $(Join-Path $distRoot 'pcontext-launcher.exe')"
Write-Host "Bundle dir: $distRoot"