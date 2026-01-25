#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Installs Moonlight Dashboard as a Windows Service using NSSM.

.DESCRIPTION
    This script installs the Moonlight Dashboard as a Windows Service
    that starts automatically on boot. It uses NSSM (Non-Sucking Service Manager)
    to wrap the Python application.

.PARAMETER InstallPath
    The path to the Moonlight Dashboard installation directory.
    Defaults to the script's parent directory.

.PARAMETER Port
    The port to run the dashboard on. Defaults to 5000.

.PARAMETER ServiceName
    The name of the Windows Service. Defaults to "MoonlightDashboard".

.EXAMPLE
    .\Install-MoonlightDashboardService.ps1

.EXAMPLE
    .\Install-MoonlightDashboardService.ps1 -Port 8080

.NOTES
    Requires NSSM to be installed. Install via: choco install nssm
    Must be run as Administrator.
#>

[CmdletBinding()]
param(
    [Parameter()]
    [string]$InstallPath = (Split-Path -Parent $PSScriptRoot),

    [Parameter()]
    [int]$Port = 5000,

    [Parameter()]
    [string]$ServiceName = "MoonlightDashboard"
)

$ErrorActionPreference = "Stop"

# Check for NSSM
$nssm = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssm) {
    Write-Error @"
NSSM (Non-Sucking Service Manager) is not installed or not in PATH.

Install it using one of these methods:
  - Chocolatey: choco install nssm
  - Scoop: scoop install nssm
  - Manual: https://nssm.cc/download
"@
    exit 1
}

# Find Python executable
$venvPython = Join-Path $InstallPath ".venv\Scripts\python.exe"
$systemPython = Get-Command python -ErrorAction SilentlyContinue

if (Test-Path $venvPython) {
    $pythonPath = $venvPython
    Write-Host "Using virtual environment Python: $pythonPath" -ForegroundColor Cyan
} elseif ($systemPython) {
    $pythonPath = $systemPython.Source
    Write-Host "Using system Python: $pythonPath" -ForegroundColor Yellow
    Write-Warning "Consider creating a virtual environment for isolation."
} else {
    Write-Error "Python not found. Please install Python 3.10+ or create a virtual environment."
    exit 1
}

# Check if service already exists
$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host "Service '$ServiceName' already exists. Stopping and removing..." -ForegroundColor Yellow
    nssm stop $ServiceName 2>$null
    nssm remove $ServiceName confirm
}

# Install the service
Write-Host "`nInstalling service '$ServiceName'..." -ForegroundColor Green

$arguments = "-m waitress --host=0.0.0.0 --port=$Port app:app"

nssm install $ServiceName $pythonPath $arguments
nssm set $ServiceName AppDirectory $InstallPath
nssm set $ServiceName DisplayName "Moonlight Dashboard"
nssm set $ServiceName Description "Workstation Manager for Apollo/Moonlight game streaming"
nssm set $ServiceName Start SERVICE_AUTO_START
nssm set $ServiceName AppStdout (Join-Path $InstallPath "logs\service.log")
nssm set $ServiceName AppStderr (Join-Path $InstallPath "logs\error.log")
nssm set $ServiceName AppRotateFiles 1
nssm set $ServiceName AppRotateBytes 1048576

# Create logs directory
$logsPath = Join-Path $InstallPath "logs"
if (-not (Test-Path $logsPath)) {
    New-Item -ItemType Directory -Path $logsPath -Force | Out-Null
}

# Start the service
Write-Host "`nStarting service..." -ForegroundColor Green
nssm start $ServiceName

# Verify
Start-Sleep -Seconds 2
$service = Get-Service -Name $ServiceName
if ($service.Status -eq "Running") {
    Write-Host "`n✓ Service installed and running successfully!" -ForegroundColor Green
    Write-Host "  Dashboard URL: http://localhost:$Port" -ForegroundColor Cyan
    Write-Host "  Service name:  $ServiceName" -ForegroundColor Cyan
    Write-Host "  Logs:          $logsPath" -ForegroundColor Cyan
} else {
    Write-Warning "Service installed but may not be running. Check logs at: $logsPath"
    Write-Host "To check status: Get-Service $ServiceName"
    Write-Host "To view logs: nssm edit $ServiceName"
}

Write-Host "`nManagement commands:" -ForegroundColor Yellow
Write-Host "  Stop:    nssm stop $ServiceName"
Write-Host "  Start:   nssm start $ServiceName"
Write-Host "  Restart: nssm restart $ServiceName"
Write-Host "  Remove:  nssm remove $ServiceName confirm"
Write-Host "  Edit:    nssm edit $ServiceName"
