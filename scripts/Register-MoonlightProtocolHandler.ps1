# Register Moonlight Protocol Handler
# Run this script once per client machine to enable moonlight:// URLs
# The handler logic is embedded directly in the registry - no external files needed

$MoonlightExe = "C:\Program Files\Moonlight Game Streaming\Moonlight.exe"

# Inline script that parses the URL and launches Moonlight
$InlineScript = @'
$url = $args[0]; if ($url -match 'moonlight://connect/([^?]+)\?app=(.+)') { & 'C:\Program Files\Moonlight Game Streaming\Moonlight.exe' stream $matches[1] ([uri]::UnescapeDataString($matches[2])) }
'@

# Build the registry command with embedded logic
$Command = "powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -Command `"$InlineScript`" `"%1`""

New-Item -Path "HKCU:\Software\Classes\moonlight\shell\open\command" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\moonlight" -Name "(Default)" -Value "URL:Moonlight Protocol"
Set-ItemProperty -Path "HKCU:\Software\Classes\moonlight" -Name "URL Protocol" -Value ""
Set-ItemProperty -Path "HKCU:\Software\Classes\moonlight\shell\open\command" -Name "(Default)" -Value $Command

Write-Host "Moonlight protocol handler registered successfully!" -ForegroundColor Green
Write-Host "No external script files required - handler is self-contained." -ForegroundColor Cyan
