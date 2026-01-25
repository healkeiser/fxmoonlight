#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Uninstalls the Moonlight Dashboard Windows Service.

.DESCRIPTION
    Stops and removes the Moonlight Dashboard Windows Service created by Install-MoonlightDashboardService.ps1.

.PARAMETER ServiceName
    The name of the Windows Service. Defaults to "MoonlightDashboard".

.EXAMPLE
    .\Uninstall-MoonlightDashboardService.ps1

.NOTES
    Must be run as Administrator.
#>

[CmdletBinding()]
param(
    [Parameter()]
    [string]$ServiceName = "MoonlightDashboard"
)

$ErrorActionPreference = "Stop"

# Check if service exists
$service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $service) {
    Write-Host "Service '$ServiceName' is not installed." -ForegroundColor Yellow
    exit 0
}

# Check for NSSM
$nssm = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssm) {
    Write-Error "NSSM not found. Cannot remove service."
    exit 1
}

Write-Host "Stopping service '$ServiceName'..." -ForegroundColor Yellow
nssm stop $ServiceName 2>$null

Write-Host "Removing service '$ServiceName'..." -ForegroundColor Yellow
nssm remove $ServiceName confirm

Write-Host "`n✓ Service '$ServiceName' has been removed." -ForegroundColor Green
