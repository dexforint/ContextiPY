[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ExePath,

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
    Write-Host "Перезапуск Explorer..."
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
        throw "Не удалось создать или открыть ключ реестра: $SubKey"
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

function Resolve-GuiExecutable {
    $venvPath = $env:VIRTUAL_ENV

    if ($venvPath) {
        $pythonwPath = Join-Path $venvPath "Scripts\pythonw.exe"
        if (Test-Path -LiteralPath $pythonwPath) {
            return (Resolve-Path -LiteralPath $pythonwPath).Path
        }

        $pythonPath = Join-Path $venvPath "Scripts\python.exe"
        if (Test-Path -LiteralPath $pythonPath) {
            return (Resolve-Path -LiteralPath $pythonPath).Path
        }
    }

    $pythonwCommand = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if ($pythonwCommand) {
        return $pythonwCommand.Source
    }

    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        return $pythonCommand.Source
    }

    throw "Не удалось определить python/pythonw для автозапуска GUI."
}

$exeFullPath = (Resolve-Path -LiteralPath $ExePath).Path
if (-not (Test-Path -LiteralPath $exeFullPath)) {
    throw "EXE не найден: $ExePath"
}

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$guiExecutable = Resolve-GuiExecutable
$guiArgs = @("-m", "pcontext.cli", "gui")

$customIconPath = Join-Path $HOME ".pcontext\icons\pcontext.ico"
if (Test-Path -LiteralPath $customIconPath) {
    $iconPath = (Resolve-Path -LiteralPath $customIconPath).Path
}
else {
    $iconPath = $exeFullPath
}

$backgroundCommand = "`"$exeFullPath`" background-show-menu --background `"%V`""
$selectionCommand = "`"$exeFullPath`" selection-show-menu --path `"%1`""

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

$runtimeDir = Join-Path $HOME ".pcontext\runtime"
$null = New-Item -ItemType Directory -Path $runtimeDir -Force

$configPath = Join-Path $runtimeDir "windows-shell-dev-config.json"
$config = [ordered]@{
    gui_executable = $guiExecutable
    gui_args = $guiArgs
    working_directory = $projectRoot
    auto_start_gui_if_missing = $true
    launcher_exe = $exeFullPath
    icon_path = $iconPath
}
Write-Utf8NoBomFile `
    -Path $configPath `
    -Content ($config | ConvertTo-Json -Depth 5)

$journalPath = Join-Path $runtimeDir "windows-background-dev-registration.json"
$journal = [ordered]@{
    created_at_utc = [DateTime]::UtcNow.ToString("o")
    exe_path = $exeFullPath
    icon_path = $iconPath
    gui_executable = $guiExecutable
    gui_args = $guiArgs
    working_directory = $projectRoot
    scopes = @(
        "Directory\Background",
        "*",
        "Directory"
    )
    background_command = $backgroundCommand
    selection_command = $selectionCommand
    menu_mode = "single_entry_opens_gui_chooser"
}

Write-Utf8NoBomFile `
    -Path $journalPath `
    -Content ($journal | ConvertTo-Json -Depth 5)

Write-Host "Безопасная dev-регистрация завершена."
Write-Host "EXE: $exeFullPath"
Write-Host "Icon: $iconPath"
Write-Host "GUI executable: $guiExecutable"
Write-Host "Scopes: Directory\Background, *, Directory"
Write-Host "Mode: single entry opens GUI chooser"
Write-Host "Config: $configPath"
Write-Host "Journal: $journalPath"

if ($RestartExplorer) {
    Restart-ExplorerSafe
}