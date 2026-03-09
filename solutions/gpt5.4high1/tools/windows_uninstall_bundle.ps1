[CmdletBinding()]
param(
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA "PContext"),
    [switch]$RestartExplorer,
    [switch]$PurgeUserData
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

function Restart-ExplorerSafe {
    Write-Host "Restarting Explorer..."
    Get-Process explorer -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Milliseconds 500
    Start-Process explorer.exe
}

function Remove-RegistryTreeIfExists {
    param([string]$Path)

    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
        Write-Host "Removed registry key: $Path"
    }
}

function Remove-RegistryValueIfExists {
    param(
        [string]$Path,
        [string]$Name
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    try {
        $null = Get-ItemProperty -LiteralPath $Path -Name $Name -ErrorAction Stop
        Remove-ItemProperty -LiteralPath $Path -Name $Name -Force
        Write-Host "Removed registry value '$Name' from: $Path"
    }
    catch {
    }
}

$resolvedInstallRoot = [System.IO.Path]::GetFullPath($InstallRoot)

Get-Process pcontext-gui -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process pcontext-launcher -ErrorAction SilentlyContinue | Stop-Process -Force

$registryPrefix = "Registry::HKEY_CURRENT_USER"
$keysToRemove = @(
    "$registryPrefix\Software\Classes\Directory\Background\shell\PContext.Dev",
    "$registryPrefix\Software\Classes\*\shell\PContext.Dev",
    "$registryPrefix\Software\Classes\Directory\shell\PContext.Dev"
)

foreach ($keyPath in $keysToRemove) {
    Remove-RegistryTreeIfExists -Path $keyPath
}

$runPath = "$registryPrefix\Software\Microsoft\Windows\CurrentVersion\Run"
Remove-RegistryValueIfExists -Path $runPath -Name "PContext"

$startMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\PContext"
if (Test-Path -LiteralPath $startMenuDir) {
    Remove-Item -LiteralPath $startMenuDir -Recurse -Force
    Write-Host "Removed Start Menu directory: $startMenuDir"
}

$runtimeDir = Join-Path $HOME ".pcontext\runtime"
foreach ($path in @(
    (Join-Path $runtimeDir "windows-shell-dev-config.json"),
    (Join-Path $runtimeDir "windows-background-dev-registration.json"),
    (Join-Path $runtimeDir "windows-launcher.log")
)) {
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Force
        Write-Host "Removed file: $path"
    }
}

if (Test-Path -LiteralPath $resolvedInstallRoot) {
    Remove-Item -LiteralPath $resolvedInstallRoot -Recurse -Force
    Write-Host "Removed install directory: $resolvedInstallRoot"
}

if ($PurgeUserData) {
    $pcontextHome = Join-Path $HOME ".pcontext"
    if (Test-Path -LiteralPath $pcontextHome) {
        Remove-Item -LiteralPath $pcontextHome -Recurse -Force
        Write-Host "Removed user data: $pcontextHome"
    }
}

Write-Host "Uninstall completed."

if ($RestartExplorer) {
    Restart-ExplorerSafe
}