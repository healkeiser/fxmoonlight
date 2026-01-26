<#
.SYNOPSIS
    Handles moonlight:// protocol URLs and launches Moonlight streaming.

.DESCRIPTION
    This script is registered as a protocol handler for moonlight:// URLs.
    It parses the URL to extract the host IP and app name, then launches
    Moonlight Game Streaming with the appropriate arguments.

.PARAMETER Url
    The moonlight:// URL to handle.
    Format: moonlight://connect/{IP}?app={AppName}

.EXAMPLE
    .\Invoke-MoonlightStream.ps1 "moonlight://connect/192.168.1.100?app=Desktop"

.EXAMPLE
    .\Invoke-MoonlightStream.ps1 "moonlight://connect/192.168.1.100?app=Steam%20Big%20Picture"

.NOTES
    Requires Moonlight Game Streaming to be installed.
    Default installation path: C:\Program Files\Moonlight Game Streaming\Moonlight.exe
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Url
)

$ErrorActionPreference = "Stop"
$MoonlightPath = "C:\Program Files\Moonlight Game Streaming\Moonlight.exe"

# Parse the URL
if ($Url -match 'moonlight://connect/([^?]+)\?app=(.+)') {
    $ip = $matches[1]
    $app = [uri]::UnescapeDataString($matches[2])

    # Verify Moonlight is installed
    if (-not (Test-Path $MoonlightPath)) {
        $message = "Moonlight not found at: $MoonlightPath`n`nPlease install Moonlight Game Streaming."
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show($message, "Moonlight Handler Error", "OK", "Error") | Out-Null
        exit 1
    }

    # Launch Moonlight
    & $MoonlightPath stream $ip $app
}
else {
    $message = "Invalid URL format: $Url`n`nExpected: moonlight://connect/{IP}?app={AppName}"
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show($message, "Moonlight Handler Error", "OK", "Error") | Out-Null
    exit 1
}
