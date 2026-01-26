<#
.SYNOPSIS
    Registers the moonlight:// protocol handler on the current machine.

.DESCRIPTION
    This script registers the moonlight:// URL protocol in the Windows registry,
    pointing to the Invoke-MoonlightStream.ps1 script for handling.

    Run this script once per client machine to enable moonlight:// URLs from
    the fxmoonlight dashboard.

.PARAMETER ScriptPath
    Path to the Invoke-MoonlightStream.ps1 script. Defaults to the same
    directory as this script.

.EXAMPLE
    .\Register-MoonlightProtocolHandler.ps1

.EXAMPLE
    .\Register-MoonlightProtocolHandler.ps1 -ScriptPath "C:\fxmoonlight\scripts\Invoke-MoonlightStream.ps1"

.NOTES
    This registers the handler for the current user only (HKCU).
    No administrator privileges required.
#>

[CmdletBinding()]
param(
    [Parameter()]
    [string]$ScriptPath = (Join-Path $PSScriptRoot "Invoke-MoonlightStream.ps1")
)

$ErrorActionPreference = "Stop"

# Verify the handler script exists
if (-not (Test-Path $ScriptPath)) {
    Write-Error "Handler script not found at: $ScriptPath"
    exit 1
}

$ScriptPath = (Resolve-Path $ScriptPath).Path

# Build the registry command
$Command = "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ScriptPath`" `"%1`""

# Register the protocol handler
Write-Host "Registering moonlight:// protocol handler..." -ForegroundColor Cyan

New-Item -Path "HKCU:\Software\Classes\moonlight\shell\open\command" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\moonlight" -Name "(Default)" -Value "URL:Moonlight Protocol"
Set-ItemProperty -Path "HKCU:\Software\Classes\moonlight" -Name "URL Protocol" -Value ""
Set-ItemProperty -Path "HKCU:\Software\Classes\moonlight\shell\open\command" -Name "(Default)" -Value $Command

Write-Host "`nMoonlight protocol handler registered successfully!" -ForegroundColor Green
Write-Host "Handler script: $ScriptPath" -ForegroundColor Cyan
Write-Host "`nYou can now use moonlight:// URLs from the dashboard." -ForegroundColor White
