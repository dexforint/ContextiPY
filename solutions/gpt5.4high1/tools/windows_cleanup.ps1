[CmdletBinding()]
param(
    [switch]$RestartExplorer,
    [switch]$PurgePContextState
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Remove-RegistryTreeIfExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
        Write-Host "Key removed: $Path"
    }
}

function Remove-RegistryValueIfExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    try {
        $null = Get-ItemProperty -LiteralPath $Path -Name $Name -ErrorAction Stop
        Remove-ItemProperty -LiteralPath $Path -Name $Name -Force
        Write-Host "Value removed '$Name' from: $Path"
    }
    catch {
        # Значение уже отсутствует — это нормально.
    }
}

function Restart-ExplorerSafe {
    Write-Host "Restarting Explorer..."
    Get-Process explorer -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Milliseconds 500
    Start-Process explorer.exe
}

$legacyClsid = "{8C5D7C56-65D0-4F31-A8AA-3101A0F1FD41}"
$devClsid = "{2EEA7982-2E08-4B7B-9C8A-5B2A0C5DE501}"

$registryPrefix = "Registry::HKEY_CURRENT_USER"

$keysToRemove = @(
    "$registryPrefix\Software\Classes\*\shellex\ContextMenuHandlers\PContext",
    "$registryPrefix\Software\Classes\Directory\shellex\ContextMenuHandlers\PContext",
    "$registryPrefix\Software\Classes\Folder\shellex\ContextMenuHandlers\PContext",
    "$registryPrefix\Software\Classes\Directory\Background\shellex\ContextMenuHandlers\PContext",
    "$registryPrefix\Software\Classes\Drive\shellex\ContextMenuHandlers\PContext",

    "$registryPrefix\Software\Classes\Directory\Background\shellex\ContextMenuHandlers\PContext.Dev",

    "$registryPrefix\Software\Classes\CLSID\$legacyClsid",
    "$registryPrefix\Software\Classes\CLSID\$devClsid"
)

foreach ($keyPath in $keysToRemove) {
    Remove-RegistryTreeIfExists -Path $keyPath
}

$approvedPath = "$registryPrefix\Software\Microsoft\Windows\CurrentVersion\Shell Extensions\Approved"
Remove-RegistryValueIfExists -Path $approvedPath -Name $legacyClsid
Remove-RegistryValueIfExists -Path $approvedPath -Name $devClsid

$journalPath = Join-Path $HOME ".pcontext\runtime\windows-shell-dev-registration.json"
if (Test-Path -LiteralPath $journalPath) {
    Remove-Item -LiteralPath $journalPath -Force
    Write-Host "Удалён journal: $journalPath"
}

if ($PurgePContextState) {
    $pcontextHome = Join-Path $HOME ".pcontext"

    $pathsToRemove = @(
        (Join-Path $pcontextHome "state.db"),
        (Join-Path $pcontextHome "runtime"),
        (Join-Path $pcontextHome "manifests"),
        (Join-Path $pcontextHome "pcontext.log")
    )

    foreach ($path in $pathsToRemove) {
        if (Test-Path -LiteralPath $path) {
            Remove-Item -LiteralPath $path -Recurse -Force
            Write-Host "Removed PContext state: $path"
        }
    }
}

if ($RestartExplorer) {
    Restart-ExplorerSafe
}

Write-Host "Очистка завершена."