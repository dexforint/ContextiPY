[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$DllPath,

    [switch]$RestartExplorer
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Set-RegistryDefaultValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string]$Value
    )

    $null = New-Item -Path $Path -Force
    Set-ItemProperty -LiteralPath $Path -Name '(default)' -Value $Value -Force
}

function Set-RegistryStringValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string]$Value
    )

    $null = New-Item -Path $Path -Force
    New-ItemProperty -LiteralPath $Path -Name $Name -Value $Value -PropertyType String -Force | Out-Null
}

function Restart-ExplorerSafe {
    Write-Host "Перезапуск Explorer..."
    Get-Process explorer -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Milliseconds 500
    Start-Process explorer.exe
}

$dllFullPath = (Resolve-Path -LiteralPath $DllPath).Path
if (-not (Test-Path -LiteralPath $dllFullPath)) {
    throw "DLL не найдена: $DllPath"
}

$devClsid = "{2EEA7982-2E08-4B7B-9C8A-5B2A0C5DE501}"
$handlerName = "PContext Dev"
$handlerKeyName = "PContext.Dev"

$registryPrefix = "Registry::HKEY_CURRENT_USER"

$clsidRoot = "$registryPrefix\Software\Classes\CLSID\$devClsid"
$inprocRoot = "$clsidRoot\InprocServer32"
$backgroundHandlerRoot = "$registryPrefix\Software\Classes\Directory\Background\shellex\ContextMenuHandlers\$handlerKeyName"
$approvedRoot = "$registryPrefix\Software\Microsoft\Windows\CurrentVersion\Shell Extensions\Approved"

Set-RegistryDefaultValue -Path $clsidRoot -Value $handlerName
Set-RegistryDefaultValue -Path $inprocRoot -Value $dllFullPath
Set-RegistryStringValue -Path $inprocRoot -Name "ThreadingModel" -Value "Apartment"

# ВАЖНО:
# На dev-этапе регистрируем только Background внутри папки.
# Это резко снижает риск поломки остальных меню Explorer.
Set-RegistryDefaultValue -Path $backgroundHandlerRoot -Value $devClsid
Set-RegistryStringValue -Path $approvedRoot -Name $devClsid -Value $handlerName

$journal = [ordered]@{
    created_at_utc = [DateTime]::UtcNow.ToString("o")
    dll_path = $dllFullPath
    clsid = $devClsid
    handler_name = $handlerName
    scope = "Directory\Background"
    keys = @(
        "HKCU\Software\Classes\CLSID\$devClsid",
        "HKCU\Software\Classes\CLSID\$devClsid\InprocServer32",
        "HKCU\Software\Classes\Directory\Background\shellex\ContextMenuHandlers\$handlerKeyName",
        "HKCU\Software\Microsoft\Windows\CurrentVersion\Shell Extensions\Approved"
    )
}

$runtimeDir = Join-Path $HOME ".pcontext\runtime"
$null = New-Item -ItemType Directory -Path $runtimeDir -Force
$journalPath = Join-Path $runtimeDir "windows-shell-dev-registration.json"
$journal | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $journalPath -Encoding UTF8

Write-Host "Dev-registration completed."
Write-Host "DLL: $dllFullPath"
Write-Host "CLSID: $devClsid"
Write-Host "Scope: Directory\Background"
Write-Host "Journal: $journalPath"

if ($RestartExplorer) {
    Restart-ExplorerSafe
}