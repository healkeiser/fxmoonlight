# Moonlight Dashboard

A workstation manager dashboard for [Apollo/Sunshine](https://github.com/LizardByte/Sunshine) and [Moonlight](https://moonlight-stream.org/) game streaming.

![Dashboard Preview](static/icon.svg)

## Features

- **Auto-Discovery**: Scan your network for Apollo/Sunshine servers
- **Hardware Detection**: Automatically retrieve GPU, CPU, RAM, and OS info via WMI/WinRM
- **App Detection**: Fetch available apps from Apollo servers
- **One-Click Streaming**: Launch Moonlight streams directly from the dashboard
- **Workstation Groups**: Organize machines into custom groups
- **Edit Workstations**: Manually update machine specs and metadata
- **Customizable Theme**: Configure site name, icon, and accent colors
- **Windows Service**: Run as a background service with automatic startup

## Requirements

### Server (where the dashboard runs)
- **Windows 10/11 or Windows Server**
- **Python 3.10+**
- Network access to workstations on port 47990 (Apollo) and 5985 (WinRM)

### Client (where you access the dashboard)
- **Web browser**
- **Moonlight Client** installed at `C:\Program Files\Moonlight Game Streaming\Moonlight.exe`
- Protocol handler registered (download from Setup in dashboard)

## Installation

### Quick Start (Development)

1. **Clone the repository**
   ```powershell
   git clone https://github.com/healkeiser/fxmoonlight.git
   cd fxmoonlight
   ```

2. **Create virtual environment and install dependencies**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. **Configure credentials** (optional, for remote WinRM/Apollo access)
   ```powershell
   Copy-Item config.example.json config.json
   # Edit config.json with your credentials
   ```

4. **Start the server**
   ```powershell
   python app.py
   ```

   The dashboard will be available at `http://localhost:5000`

### Production (Windows Service)

1. **Install NSSM** (Non-Sucking Service Manager)
   ```powershell
   # Using Chocolatey
   choco install nssm

   # Or Scoop
   scoop install nssm
   ```

2. **Run the install script** (as Administrator)
   ```powershell
   .\scripts\Install-MoonlightDashboardService.ps1
   ```

3. The service will start automatically and run on boot.

**Service management:**
```powershell
nssm stop MoonlightDashboard      # Stop
nssm start MoonlightDashboard     # Start
nssm restart MoonlightDashboard   # Restart
nssm edit MoonlightDashboard      # Edit configuration
```

To uninstall:
```powershell
.\scripts\Uninstall-MoonlightDashboardService.ps1
```

## Client Setup

1. Open the dashboard in your browser
2. Click **Setup** in the navbar (orange button)
3. Download and run the `.reg` file to register the protocol handler
4. Test with the **Test Protocol Handler** button

### Pairing Moonlight Clients

Each device running Moonlight must be paired with the host PC:

1. Open **Moonlight** on your client device (phone, tablet, PC, etc.)
2. Your host PC should appear automatically. Tap/click on it.
3. Moonlight will display a **4-digit PIN**
4. Open the **Apollo/Sunshine Web UI** on your host PC (gear icon on workstation cards)
5. Go to **PIN** tab and enter the code
6. The client is now paired and can stream from that host

## Usage

### Workstation Cards

Each workstation card displays:
- **Name and IP**: Machine identifier with "This Server" badge if running the dashboard
- **Status indicator**: Green (online) or red (offline)
- **Hardware specs**: GPU, RAM badges
- **App buttons**: Launch Moonlight streams for each detected app

### Card Actions

| Button | Action |
|--------|--------|
| Gear | Open Apollo/Sunshine Web UI |
| Pencil | Edit workstation (name, group, specs) |
| Refresh | Probe for updated info from Apollo |
| Trash | Delete workstation |

### Groups

Organize workstations by assigning them to groups:

1. Click the **pencil** button on a workstation card
2. Select an existing group or create a new one
3. Save changes

Grouped workstations appear under collapsible headers with counts.

## Project Structure

```
moonlight-dashboard/
├── app.py                 # Flask backend
├── requirements.txt       # Python dependencies
├── config.example.json    # Configuration template (copy to config.json)
├── config.json            # Your config with credentials (gitignored)
├── workstations.json      # Workstation data storage (gitignored)
├── templates/
│   ├── index.html         # Main page layout
│   └── components/        # Reusable UI components
│       ├── workstation-card.html   # Workstation card
│       ├── modal-setup.html        # Setup/pairing instructions
│       ├── modal-discover.html     # Network discovery
│       ├── modal-edit.html         # Edit workstation
│       └── modal-confirm.html      # Confirmation dialogs
├── static/
│   ├── icon.svg           # App icon (customizable)
│   ├── css/
│   │   └── main.css       # All styles (uses CSS variables for theming)
│   └── js/
│       └── app.js         # All JavaScript (API, discovery, forms)
└── scripts/
    ├── Install-MoonlightDashboardService.ps1   # Install as Windows Service
    ├── Uninstall-MoonlightDashboardService.ps1 # Remove Windows Service
    └── Register-MoonlightProtocolHandler.ps1   # Alternative client setup (PowerShell)
```

## Protocol Handler

The `moonlight://` protocol handler allows launching streams from browser links:

```
moonlight://connect/{ip}?app={appname}
```

**Examples:**
- `moonlight://connect/192.168.1.10?app=Desktop`
- `moonlight://connect/192.168.1.10?app=Steam%20Big%20Picture`

The handler is registered directly in the Windows registry with embedded logic - no external script files are required after registration.

## Configuration

### config.json

Copy `config.example.json` to `config.json` and configure:

```json
{
  "site": {
    "name": "Moonlight Dashboard",
    "icon": "/static/icon.svg",
    "accent_color": "#fd4301",
    "accent_color_hover": "#e63d00"
  },
  "credentials": {
    "winrm_user": "${WINRM_USER:-Administrator}",
    "winrm_password": "${WINRM_PASSWORD}",
    "apollo_user": "${APOLLO_USER:-admin}",
    "apollo_password": "${APOLLO_PASSWORD}"
  },
  "network": {
    "subnet": "192.168.1",
    "scan_start": 1,
    "scan_end": 254
  },
  "server_port": 5000,
  "apollo_port": 47990,
  "scan_timeout": 1
}
```

| Field | Purpose |
|-------|--------|
| `site.name` | Dashboard title shown in navbar and browser tab |
| `site.icon` | Path to favicon/logo (SVG recommended) |
| `site.accent_color` | Primary accent color (hex) |
| `site.accent_color_hover` | Hover state accent color (hex) |
| `winrm_user/password` | Query remote Windows machines for hardware specs via WinRM |
| `apollo_user/password` | Apollo/Sunshine web UI credentials for API access |
| `network.*` | Default subnet and range for discovery scans |
| `server_port` | Dashboard server port (default: 5000) |
| `apollo_port` | Apollo/Sunshine API port (default: 47990) |
| `scan_timeout` | Socket timeout in seconds for network scans (default: 1) |

### Apollo Authentication

The dashboard uses session-based authentication with Apollo/Sunshine. Configure your Apollo username and password in `config.json`:

```json
"credentials": {
  "apollo_user": "your_username",
  "apollo_password": "your_password"
}
```

> **Note:** All Apollo servers must share the same username/password for authentication to work across all machines.

### Environment Variables

For security, **passwords can be stored in environment variables** instead of the config file. Use the `${VAR}` syntax:

| Syntax | Behavior |
|--------|----------|
| `${VAR}` | Replaced with env var value (empty string if not set) |
| `${VAR:-default}` | Use env var value, or `default` if not set |

**Setting environment variables (PowerShell):**

```powershell
# Session only (for testing)
$env:WINRM_PASSWORD = "your-password"
$env:APOLLO_PASSWORD = "your-password"

# Persistent (user level)
[Environment]::SetEnvironmentVariable("WINRM_PASSWORD", "your-password", "User")
[Environment]::SetEnvironmentVariable("APOLLO_PASSWORD", "your-password", "User")

# Persistent (machine level, requires Admin)
[Environment]::SetEnvironmentVariable("WINRM_PASSWORD", "your-password", "Machine")
```

**For Windows Service (NSSM):**

```powershell
nssm set MoonlightDashboard AppEnvironmentExtra WINRM_PASSWORD=your-password APOLLO_PASSWORD=your-password
nssm restart MoonlightDashboard
```

### Enabling WinRM on Workstations

For remote hardware detection to work, enable WinRM on each workstation:

```powershell
# Run as Administrator on each workstation
Enable-PSRemoting -Force
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
```

### Moonlight Path

If Moonlight is installed in a non-standard location, the path is embedded in the `.reg` file downloaded from the dashboard. You'll need to:

1. Download the `.reg` file from Setup
2. Open it in a text editor
3. Change `C:\\Program Files\\Moonlight Game Streaming\\Moonlight.exe` to your path
4. Run the modified `.reg` file

## Troubleshooting

### "Moonlight not launching from browser"
- Ensure you've downloaded and run the `.reg` file from Setup
- Check that Moonlight is installed at `C:\Program Files\Moonlight Game Streaming\Moonlight.exe`
- Try the URL directly: `moonlight://connect/YOUR_IP?app=Desktop`

### "Discovery not finding machines"
- Ensure Apollo/Sunshine is running (default port: 47990)
- Check firewall rules allow traffic on the Apollo port
- Verify the target machines are on the expected subnet
- Try increasing `scan_timeout` in config.json for slower networks

### "Hardware info incorrect or missing"
- Local machine: Uses WMI directly (most accurate)
- Remote machines: Requires WinRM credentials configured in config.json
- If WinRM fails, only hostname from DNS is shown
- You can manually edit workstation specs using the pencil button

### "Apps not detected"
- Ensure Apollo credentials are configured in config.json
- All Apollo servers must use the same username/password
- Click the refresh button on the workstation card to re-probe

## License

MIT License
