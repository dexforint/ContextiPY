[CmdletBinding()]
param(
    [string]$SourceDir = "",
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA "PContext"),
    [switch]$SkipShellRegistration,
    [switch]$EnableAutostart,
    [switch]$RestartExplorer
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

function Write-Utf8NoBomFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

function Restart-ExplorerSafe {
    Write-Host "Restarting Explorer..."
    Get-Process explorer -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Milliseconds 500
    Start-Process explorer.exe
}

function New-OrOpen-RegistryKey {
    param(
        [Parameter(Mandatory = $true)]
        [Microsoft.Win32.RegistryKey]$BaseKey,

        [Parameter(Mandatory = $true)]
        [string]$SubKey
    )

    $key = $BaseKey.CreateSubKey($SubKey)
    if ($null -eq $key) {
        throw "Failed to create or open registry key: $SubKey"
    }

    return $key
}

function Register-PContextSingleEntry {
    param(
        [Parameter(Mandatory = $true)]
        [Microsoft.Win32.RegistryKey]$ClassesRoot,

        [Parameter(Mandatory = $true)]
        [string]$RootSubKey,

        [Parameter(Mandatory = $true)]
        [string]$IconPath,

        [Parameter(Mandatory = $true)]
        [string]$CommandText
    )

    $rootKey = New-OrOpen-RegistryKey -BaseKey $ClassesRoot -SubKey $RootSubKey
    try {
        $rootKey.SetValue("MUIVerb", "PContext", [Microsoft.Win32.RegistryValueKind]::String)
        $rootKey.SetValue("Icon", $IconPath, [Microsoft.Win32.RegistryValueKind]::String)
    }
    finally {
        $rootKey.Close()
    }

    $commandKey = New-OrOpen-RegistryKey -BaseKey $ClassesRoot -SubKey "$RootSubKey\command"
    try {
        $commandKey.SetValue("", $CommandText, [Microsoft.Win32.RegistryValueKind]::String)
    }
    finally {
        $commandKey.Close()
    }
}

function Set-WindowsAutostart {
    param(
        [Parameter(Mandatory = $true)]
        [string]$GuiExePath
    )

    $command = [System.String]::Format('"{0}" --hidden', $GuiExePath)

    $hkcu = [Microsoft.Win32.RegistryKey]::OpenBaseKey(
        [Microsoft.Win32.RegistryHive]::CurrentUser,
        [Microsoft.Win32.RegistryView]::Default
    )

    try {
        $runKey = $hkcu.CreateSubKey("Software\Microsoft\Windows\CurrentVersion\Run")
        if ($null -eq $runKey) {
            throw "Failed to open Windows autostart registry key."
        }

        try {
            $runKey.SetValue("PContext", $command, [Microsoft.Win32.RegistryValueKind]::String)
        }
        finally {
            $runKey.Close()
        }
    }
    finally {
        $hkcu.Close()
    }
}

function Create-Shortcut {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ShortcutPath,

        [Parameter(Mandatory = $true)]
        [string]$TargetPath,

        [string]$Arguments = "",

        [string]$WorkingDirectory = "",

        [string]$IconLocation = ""
    )

    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $TargetPath
    $shortcut.Arguments = $Arguments

    if ($WorkingDirectory) {
        $shortcut.WorkingDirectory = $WorkingDirectory
    }

    if ($IconLocation) {
        $shortcut.IconLocation = $IconLocation
    }

    $shortcut.Save()
}

if ([string]::IsNullOrWhiteSpace($SourceDir)) {
    if (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) {
        $SourceDir = $PSScriptRoot
    }
    else {
        $SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    }
}

$resolvedSourceDir = (Resolve-Path -LiteralPath $SourceDir).Path
$resolvedInstallRoot = [System.IO.Path]::GetFullPath($InstallRoot)

$sourceGuiExe = Join-Path $resolvedSourceDir "pcontext-gui.exe"
$sourceLauncherExe = Join-Path $resolvedSourceDir "pcontext-launcher.exe"
$sourceReadme = Join-Path $resolvedSourceDir "README.txt"
$sourceUninstallScript = Join-Path $resolvedSourceDir "windows_uninstall_bundle.ps1"
$sourceSrcDir = Join-Path $resolvedSourceDir "src"

foreach ($requiredPath in @($sourceGuiExe, $sourceLauncherExe, $sourceUninstallScript, $sourceSrcDir)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required bundle file not found: $requiredPath"
    }
}

$appDir = Join-Path $resolvedInstallRoot "app"
$null = New-Item -ItemType Directory -Path $appDir -Force

$installedGuiExe = Join-Path $appDir "pcontext-gui.exe"
$installedLauncherExe = Join-Path $appDir "pcontext-launcher.exe"
$installedReadme = Join-Path $appDir "README.txt"
$installedSrcDir = Join-Path $appDir "src"
$installedUninstallScript = Join-Path $resolvedInstallRoot "windows_uninstall_bundle.ps1"

Copy-Item -LiteralPath $sourceGuiExe -Destination $installedGuiExe -Force
Copy-Item -LiteralPath $sourceLauncherExe -Destination $installedLauncherExe -Force

if (Test-Path -LiteralPath $sourceReadme) {
    Copy-Item -LiteralPath $sourceReadme -Destination $installedReadme -Force
}

if (Test-Path -LiteralPath $installedSrcDir) {
    Remove-Item -LiteralPath $installedSrcDir -Recurse -Force
}
Copy-Item -LiteralPath $sourceSrcDir -Destination $installedSrcDir -Recurse -Force

Copy-Item -LiteralPath $sourceUninstallScript -Destination $installedUninstallScript -Force

$iconPath = $installedGuiExe
$projectWorkingDirectory = $appDir

$backgroundCommand = "`"$installedLauncherExe`" background-show-menu --background `"%V`""
$selectionCommand = "`"$installedLauncherExe`" selection-show-menu --path `"%1`""

if (-not $SkipShellRegistration) {
    $hkcu = [Microsoft.Win32.RegistryKey]::OpenBaseKey(
        [Microsoft.Win32.RegistryHive]::CurrentUser,
        [Microsoft.Win32.RegistryView]::Default
    )

    try {
        $classesRoot = New-OrOpen-RegistryKey -BaseKey $hkcu -SubKey "Software\Classes"
        try {
            Register-PContextSingleEntry `
                -ClassesRoot $classesRoot `
                -RootSubKey "Directory\Background\shell\PContext.Dev" `
                -IconPath $iconPath `
                -CommandText $backgroundCommand

            Register-PContextSingleEntry `
                -ClassesRoot $classesRoot `
                -RootSubKey "*\shell\PContext.Dev" `
                -IconPath $iconPath `
                -CommandText $selectionCommand

            Register-PContextSingleEntry `
                -ClassesRoot $classesRoot `
                -RootSubKey "Directory\shell\PContext.Dev" `
                -IconPath $iconPath `
                -CommandText $selectionCommand
        }
        finally {
            $classesRoot.Close()
        }
    }
    finally {
        $hkcu.Close()
    }
}

$runtimeDir = Join-Path $HOME ".pcontext\runtime"
$null = New-Item -ItemType Directory -Path $runtimeDir -Force

$configPath = Join-Path $runtimeDir "windows-shell-dev-config.json"
$config = [ordered]@{
    gui_executable = $installedGuiExe
    gui_args = @("--hidden")
    working_directory = $projectWorkingDirectory
    auto_start_gui_if_missing = $true
    launcher_exe = $installedLauncherExe
    icon_path = $iconPath
}
Write-Utf8NoBomFile -Path $configPath -Content ($config | ConvertTo-Json -Depth 5)

$manifestPath = Join-Path $resolvedInstallRoot "install-manifest.json"
$manifest = [ordered]@{
    installed_at_utc = [DateTime]::UtcNow.ToString("o")
    install_root = $resolvedInstallRoot
    app_dir = $appDir
    gui_exe = $installedGuiExe
    launcher_exe = $installedLauncherExe
    src_dir = $installedSrcDir
    uninstall_script = $installedUninstallScript
    shell_registered = (-not $SkipShellRegistration)
    autostart_enabled = $EnableAutostart.IsPresent
}
Write-Utf8NoBomFile -Path $manifestPath -Content ($manifest | ConvertTo-Json -Depth 5)

$startMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\PContext"
$null = New-Item -ItemType Directory -Path $startMenuDir -Force

Create-Shortcut `
    -ShortcutPath (Join-Path $startMenuDir "PContext.lnk") `
    -TargetPath $installedGuiExe `
    -Arguments "" `
    -WorkingDirectory $projectWorkingDirectory `
    -IconLocation $iconPath

Create-Shortcut `
    -ShortcutPath (Join-Path $startMenuDir "Uninstall PContext.lnk") `
    -TargetPath "powershell.exe" `
    -Arguments "-ExecutionPolicy Bypass -File `"$installedUninstallScript`" -RestartExplorer" `
    -WorkingDirectory $resolvedInstallRoot `
    -IconLocation $iconPath

if ($EnableAutostart) {
    Set-WindowsAutostart -GuiExePath $installedGuiExe
}

Write-Host "Installation completed."
Write-Host "Install root: $resolvedInstallRoot"
Write-Host "GUI exe: $installedGuiExe"
Write-Host "Launcher exe: $installedLauncherExe"
Write-Host "Src dir: $installedSrcDir"
Write-Host "Start Menu: $startMenuDir"
Write-Host "Shell registration: $(if ($SkipShellRegistration) { 'skipped' } else { 'done' })"
Write-Host "Autostart: $(if ($EnableAutostart) { 'enabled' } else { 'disabled' })"

if ($RestartExplorer) {
    Restart-ExplorerSafe
}