"""
Moonlight Dashboard: Workstation Manager for Apollo/Moonlight Streaming
A web-based dashboard for managing remote workstations.
"""

# Built-in
import concurrent.futures
import json
import os
import re
import socket
import ssl
import urllib.request
from datetime import datetime
from typing import Any

# Third-party
from flask import Flask, render_template, request, jsonify, Response

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "FXMOONLIGHT_SECRET_KEY", "fxmoonlight-secret-key"
)

# File paths (configurable via environment variables for Docker)
DATA_FILE = os.environ.get("FXMOONLIGHT_DATA_FILE", "data.json")
CONFIG_FILE = os.environ.get("FXMOONLIGHT_CONFIG_FILE", "config.json")

# Optional WMI import (Windows-only)
try:
    import wmi

    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False


def resolve_env_vars(obj: str | dict | list | Any) -> str | dict | list | Any:
    """Recursively resolve ${VAR} patterns in config values.

    Supports ${VAR} for simple substitution and ${VAR:-default} for
    default values when the environment variable is not set.

    Args:
        obj: The configuration object to process. Can be a string,
            dict, list, or any other type (passed through unchanged).

    Returns:
        The same type as input with environment variables resolved.
        Nested structures are processed recursively.
    """
    if isinstance(obj, str):
        # Replace ${VAR} or ${VAR:-default} patterns
        def replacer(match):
            var_name = match.group(1)
            default = match.group(3)  # None if no default specified
            return os.environ.get(var_name, default if default else "")

        return re.sub(r"\$\{([^}:-]+)(:-(.*?))?\}", replacer, obj)
    elif isinstance(obj, dict):
        return {k: resolve_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [resolve_env_vars(item) for item in obj]
    return obj


def load_config() -> dict[str, Any]:
    """Load configuration from config.json.

    Merges user config with defaults and resolves environment variables.
    If config.json doesn't exist or is invalid, returns defaults.

    Returns:
        Configuration dictionary with all settings.
    """
    default_config = {
        "site": {
            "name": "Moonlight Dashboard",
            "icon": "/static/icon.svg",
            "accent_color": "#fd4301",
            "accent_color_hover": "#e63d00",
        },
        "credentials": {
            "winrm_user": "",
            "winrm_password": "",
            "apollo_user": "",
            "apollo_password": "",
        },
        "network": {
            "subnet": "192.168.1",
            "scan_start": 1,
            "scan_end": 254,
        },
        "server_port": 5000,
        "apollo_ports": [47990],
        "scan_timeout": 1,
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                # Merge with defaults
                for key in default_config:
                    if key not in config:
                        config[key] = default_config[key]
                # Resolve environment variables
                return resolve_env_vars(config)
        except Exception:
            pass
    return default_config


def get_credentials() -> dict[str, str]:
    """Get credentials from config.

    Returns:
        Dictionary with winrm_user, winrm_password, apollo_user,
        and apollo_password keys.
    """
    config = load_config()
    return config.get("credentials", {})


def get_site_config() -> dict[str, str]:
    """Get site theming configuration.

    Returns:
        Dictionary with name, icon, accent_color, and accent_color_hover.
    """
    config = load_config()
    return config.get(
        "site",
        {
            "name": "Moonlight Dashboard",
            "icon": "/static/icon.svg",
            "accent_color": "#fd4301",
            "accent_color_hover": "#e63d00",
        },
    )


def get_network_config() -> dict[str, Any]:
    """Get network scanning configuration.

    Returns:
        Dictionary with subnet, scan_start, and scan_end keys.
    """
    config = load_config()
    return config.get(
        "network", {"subnet": "192.168.1", "scan_start": 1, "scan_end": 254}
    )


def get_server_port() -> int:
    """Get dashboard server port from config.

    Returns:
        Port number for the Flask server (default: 5000).
    """
    return load_config().get("server_port", 5000)


def get_apollo_ports() -> list[int]:
    """Get Apollo API ports from config.

    Supports both new 'apollo_ports' array and legacy 'apollo_port' single value.

    Returns:
        List of port numbers for Apollo/Sunshine API (default: [47990]).
    """
    config = load_config()
    # Support new apollo_ports array format
    if "apollo_ports" in config:
        ports = config["apollo_ports"]
        if isinstance(ports, list):
            return ports
        return [ports]  # Single value provided as non-list
    # Backward compatibility with old apollo_port single value
    if "apollo_port" in config:
        return [config["apollo_port"]]
    return [47990]


def get_primary_apollo_port() -> int:
    """Get the primary (first) Apollo API port from config.

    Returns:
        Primary port number for Apollo/Sunshine API (default: 47990).
    """
    ports = get_apollo_ports()
    return ports[0] if ports else 47990


def get_scan_timeout() -> int:
    """Get network scan timeout from config.

    Returns:
        Timeout in seconds for socket connections (default: 1).
    """
    return load_config().get("scan_timeout", 1)


def get_remote_machine_info_winrm(ip: str) -> dict[str, str | None]:
    """Get hardware info from a remote Windows machine using WinRM.

    Connects to the remote machine via WinRM and runs PowerShell commands
    to retrieve hardware information. Requires valid credentials in config.

    Args:
        ip: IP address of the remote Windows machine.

    Returns:
        Dictionary with hostname, gpu, ram, os, and cpu keys.
        Values are None if retrieval failed.
    """
    info = {
        "hostname": None,
        "gpu": None,
        "ram": None,
        "os": None,
        "cpu": None,
    }

    creds = get_credentials()
    user = creds.get("winrm_user", "")
    password = creds.get("winrm_password", "")

    if not user or not password:
        # No credentials configured, skip WinRM
        return info

    try:
        import winrm

        session = winrm.Session(
            target=ip,
            auth=(user, password),
            transport="ntlm",
            server_cert_validation="ignore",
        )

        # Get all info in one PowerShell call for efficiency
        ps_script = """
$gpu = (Get-WmiObject Win32_VideoController | Where-Object { $_.Name -notmatch 'Microsoft|Basic|Parsec|Virtual|Remote' } | Select-Object -First 1).Name
if (-not $gpu) { $gpu = (Get-WmiObject Win32_VideoController | Select-Object -First 1).Name }
$cpu = (Get-WmiObject Win32_Processor | Select-Object -First 1).Name
$os = (Get-WmiObject Win32_OperatingSystem).Caption -replace 'Microsoft ',''
$ram = [math]::Round((Get-WmiObject Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
$hostname = $env:COMPUTERNAME

@{
    hostname = $hostname
    gpu = $gpu
    cpu = $cpu
    os = $os
    ram = $ram
} | ConvertTo-Json
"""
        result = session.run_ps(ps_script)

        if result.status_code == 0:
            data = json.loads(result.std_out.decode("utf-8"))
            info["hostname"] = data.get("hostname", "").upper()
            info["gpu"] = data.get("gpu")
            info["cpu"] = (
                data.get("cpu", "").strip() if data.get("cpu") else None
            )
            info["os"] = data.get("os")
            ram = data.get("ram")
            if ram:
                # Round to nearest standard size
                standard_sizes = [8, 16, 32, 64, 128, 256, 512]
                ram_gb = min(standard_sizes, key=lambda x: abs(x - int(ram)))
                info["ram"] = f"{ram_gb}GB"

    except ImportError:
        # pywinrm not installed
        pass
    except Exception as e:
        # WinRM failed (firewall, credentials, etc.)
        pass

    return info


def load_workstations() -> dict[str, list]:
    """Load workstations from JSON file.

    Returns:
        Dictionary with 'workstations' key containing list of workstation dicts.
        Returns empty list if file doesn't exist.
    """
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"workstations": []}


def save_workstations(data: dict[str, list]) -> None:
    """Save workstations to JSON file.

    Args:
        data: Dictionary with 'workstations' key containing list of workstation dicts.
    """
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_groups() -> dict[str, dict]:
    """Load group metadata from data.json.

    Returns:
        Dictionary with 'groups' key containing group name to metadata mapping.
        Returns empty dict if file doesn't exist or has no groups.
    """
    data = load_workstations()
    return {"groups": data.get("groups", {})}


def save_groups(groups_data: dict[str, dict]) -> None:
    """Save group metadata to data.json.

    Args:
        groups_data: Dictionary with 'groups' key containing group metadata.
    """
    data = load_workstations()
    data["groups"] = groups_data.get("groups", {})
    save_workstations(data)


def get_group_icon(group_name: str) -> str:
    """Get the icon class for a group.

    Args:
        group_name: Name of the group.

    Returns:
        Bootstrap icon class string, defaults to 'bi-folder' if not set.
    """
    groups_data = load_groups()
    group_info = groups_data.get("groups", {}).get(group_name, {})
    return group_info.get("icon", "bi-folder")


def check_apollo_port(ip: str, port: int | None = None) -> bool:
    """Check if Apollo port is open on the given IP.

    Args:
        ip: IP address to check.
        port: Specific port to check. If None, uses primary configured port.

    Returns:
        True if Apollo port is reachable, False otherwise.
    """
    if port is None:
        port = get_primary_apollo_port()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(get_scan_timeout())
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def check_apollo_ports(ip: str) -> list[int]:
    """Check which Apollo ports are open on the given IP.

    Args:
        ip: IP address to check.

    Returns:
        List of open Apollo ports.
    """
    open_ports = []
    for port in get_apollo_ports():
        if check_apollo_port(ip, port):
            open_ports.append(port)
    return open_ports


def is_local_ip(ip: str) -> bool:
    """Check if an IP address belongs to the local machine.

    Args:
        ip: IP address to check.

    Returns:
        True if the IP belongs to a local network interface.
    """
    try:
        local_ips = socket.gethostbyname_ex(socket.gethostname())[2]
        return ip in local_ips
    except Exception:
        return False


def get_local_machine_info() -> dict[str, str | None]:
    """Get hardware info for the local machine using WMI.

    Retrieves GPU, CPU, RAM, and OS information from the local Windows
    machine. Prioritizes discrete GPUs over integrated graphics.

    Returns:
        Dictionary with hostname, gpu, ram, os, and cpu keys.
        Falls back to platform module if WMI is unavailable.
    """
    info = {
        "hostname": socket.gethostname().upper(),
        "gpu": None,
        "ram": None,
        "os": None,
        "cpu": None,
    }

    if WMI_AVAILABLE:
        try:
            c = wmi.WMI()

            # OS info from WMI (e.g., "Microsoft Windows 11 Pro")
            for os_info in c.Win32_OperatingSystem():
                if os_info.Caption:
                    # Clean up the name
                    os_name = os_info.Caption.replace("Microsoft ", "")
                    info["os"] = os_name
                    break

            # CPU info from WMI (e.g., "AMD Ryzen 9 7950X 16-Core Processor")
            for cpu in c.Win32_Processor():
                if cpu.Name:
                    info["cpu"] = cpu.Name.strip()
                    break

            # RAM from WMI - round to nearest standard size
            for cs in c.Win32_ComputerSystem():
                if cs.TotalPhysicalMemory:
                    ram_bytes = int(cs.TotalPhysicalMemory)
                    ram_gb_raw = ram_bytes / (1024**3)
                    # Round to nearest standard RAM size (8, 16, 32, 64, 128, 256, 512)
                    standard_sizes = [8, 16, 32, 64, 128, 256, 512]
                    ram_gb = min(
                        standard_sizes, key=lambda x: abs(x - ram_gb_raw)
                    )
                    info["ram"] = f"{ram_gb}GB"
                    break

            # GPU from WMI - prioritize discrete GPUs
            all_gpus = [
                gpu.Name for gpu in c.Win32_VideoController() if gpu.Name
            ]

            # Skip list: virtual adapters and basic drivers
            skip_keywords = [
                "Microsoft",
                "Basic",
                "Parsec",
                "Virtual",
                "Remote",
            ]

            # Priority list: discrete GPU brands/keywords (checked in order)
            priority_keywords = [
                "NVIDIA",
                "GeForce",
                "RTX",
                "GTX",
                "Quadro",
                "Radeon RX",
                "Radeon Pro",
            ]

            # First pass: find priority discrete GPU
            for priority in priority_keywords:
                for gpu_name in all_gpus:
                    if priority.lower() in gpu_name.lower():
                        info["gpu"] = gpu_name
                        break
                if info["gpu"]:
                    break

            # Second pass: any GPU not in skip list
            if not info["gpu"]:
                for gpu_name in all_gpus:
                    if not any(
                        skip.lower() in gpu_name.lower()
                        for skip in skip_keywords
                    ):
                        info["gpu"] = gpu_name
                        break

            # Fallback: first GPU with a name
            if not info["gpu"] and all_gpus:
                info["gpu"] = all_gpus[0]

        except Exception:
            pass
    else:
        # Fallback to platform module if WMI not available
        import platform

        info["os"] = f"{platform.system()} {platform.release()}"
        info["cpu"] = platform.processor() or None

    return info


def get_machine_info_wmi(ip: str) -> dict[str, str | None]:
    """Get machine info using WMI (local) or WinRM (remote).

    Automatically detects if the IP is local and uses the appropriate
    method. For remote machines, requires WinRM credentials in config.

    Args:
        ip: IP address of the target machine.

    Returns:
        Dictionary with hostname, gpu, ram, os, and cpu keys.
    """
    info = {"hostname": None, "gpu": None, "ram": None, "os": None, "cpu": None}

    # If this is the local machine, use local detection
    if is_local_ip(ip):
        return get_local_machine_info()

    # For remote machines, try WinRM first
    winrm_info = get_remote_machine_info_winrm(ip)
    if any(winrm_info.get(k) for k in ["gpu", "ram", "os", "cpu"]):
        # WinRM worked, use that data
        return winrm_info

    # Fallback: DNS lookup for hostname only
    try:
        hostname = socket.gethostbyaddr(ip)[0]
        info["hostname"] = hostname.split(".")[0].upper()
    except OSError:
        pass

    return info


def get_apollo_session(
    ip: str, port: int | None = None
) -> tuple[ssl.SSLContext, str | None, str, int]:
    """Get an authenticated session for Apollo API calls.

    Args:
        ip: IP address of the Apollo server.
        port: Specific port to use. If None, uses primary configured port.

    Returns:
        Tuple of (ssl_context, auth_cookie, api_host, port).
    """
    is_local = is_local_ip(ip)
    api_host = "localhost" if is_local else ip
    apollo_port = port if port is not None else get_primary_apollo_port()

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # Get credentials for session-based auth
    creds = get_credentials()
    apollo_user = creds.get("apollo_user", "")
    apollo_password = creds.get("apollo_password", "")

    auth_cookie = None
    if apollo_user and apollo_password:
        try:
            login_url = f"https://{api_host}:{apollo_port}/api/login"
            login_data = json.dumps(
                {"username": apollo_user, "password": apollo_password}
            ).encode()
            login_req = urllib.request.Request(
                login_url,
                data=login_data,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(
                login_req, timeout=3, context=ctx
            ) as response:
                cookie_header = response.headers.get("Set-Cookie", "")
                if "auth=" in cookie_header:
                    for part in cookie_header.split(";"):
                        if part.strip().startswith("auth="):
                            auth_cookie = part.strip()
                            break
        except Exception:
            pass

    return ctx, auth_cookie, api_host, apollo_port


def get_paired_clients(
    ip: str, port: int | None = None
) -> list[dict[str, Any]]:
    """Get list of paired Moonlight clients from Apollo.

    Args:
        ip: IP address of the Apollo server.
        port: Specific port to use. If None, uses primary configured port.

    Returns:
        List of paired client dictionaries with name and uuid.
    """
    clients = []

    try:
        ctx, auth_cookie, api_host, apollo_port = get_apollo_session(ip, port)

        headers = {"Accept": "application/json"}
        if auth_cookie:
            headers["Cookie"] = auth_cookie

        clients_url = f"https://{api_host}:{apollo_port}/api/clients"
        req = urllib.request.Request(clients_url, headers=headers)

        with urllib.request.urlopen(req, timeout=3, context=ctx) as response:
            data = json.loads(response.read().decode())

            # Handle different response formats
            if isinstance(data, dict) and "named_certs" in data:
                # Sunshine format: {"named_certs": [{"name": "...", ...}]}
                clients = data.get("named_certs", [])
            elif isinstance(data, dict) and "clients" in data:
                clients = data.get("clients", [])
            elif isinstance(data, list):
                clients = data

    except Exception:
        pass

    return clients


def get_machine_info_apollo(ip: str, port: int | None = None) -> dict[str, Any]:
    """Get machine info from Apollo's API endpoints.

    Queries the Apollo/Sunshine API for hostname and available apps.
    For local machines, also retrieves hardware specs via WMI.

    Args:
        ip: IP address of the Apollo server.
        port: Specific port to use. If None, uses primary configured port.

    Returns:
        Dictionary with hostname, gpu, ram, os, cpu, apps, and instance_name keys.
    """
    info = {
        "hostname": None,
        "gpu": None,
        "ram": None,
        "os": None,
        "apps": [],
        "instance_name": None,
    }

    # Determine if this is the local machine
    is_local = is_local_ip(ip)
    api_host = "localhost" if is_local else ip
    apollo_port = port if port is not None else get_primary_apollo_port()

    # Get credentials for session-based auth
    creds = get_credentials()
    apollo_user = creds.get("apollo_user", "")
    apollo_password = creds.get("apollo_password", "")

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        # Get session cookie by logging in
        auth_cookie = None
        if apollo_user and apollo_password:
            try:
                login_url = f"https://{api_host}:{apollo_port}/api/login"
                login_data = json.dumps(
                    {"username": apollo_user, "password": apollo_password}
                ).encode()
                login_req = urllib.request.Request(
                    login_url,
                    data=login_data,
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(
                    login_req, timeout=3, context=ctx
                ) as response:
                    # Extract auth cookie from Set-Cookie header
                    cookie_header = response.headers.get("Set-Cookie", "")
                    if "auth=" in cookie_header:
                        # Parse the auth token from the cookie
                        for part in cookie_header.split(";"):
                            if part.strip().startswith("auth="):
                                auth_cookie = part.strip()
                                break
            except Exception:
                pass  # Login failed, continue without auth

        # Helper to make authenticated requests using session cookie
        def make_request(url):
            headers = {"Accept": "application/json"}
            if auth_cookie:
                headers["Cookie"] = auth_cookie
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(
                req, timeout=3, context=ctx
            ) as response:
                return json.loads(response.read().decode())

        # Try to get apps list from Apollo API
        try:
            apps_url = f"https://{api_host}:{apollo_port}/api/apps"
            data = make_request(apps_url)
            # Response contains an "apps" array with app objects
            if isinstance(data, dict) and "apps" in data:
                info["apps"] = [
                    (
                        app.get("name", str(app))
                        if isinstance(app, dict)
                        else str(app)
                    )
                    for app in data["apps"]
                ]
            elif isinstance(data, list):
                # Fallback for older API format
                info["apps"] = [
                    (
                        app.get("name", str(app))
                        if isinstance(app, dict)
                        else str(app)
                    )
                    for app in data
                ]
        except Exception:
            pass

        # Try to get config/info from Apollo
        endpoints = [
            f"https://{api_host}:{apollo_port}/api/config",
            f"https://{api_host}:{apollo_port}/api/currentClient",
        ]

        for endpoint in endpoints:
            try:
                data = make_request(endpoint)

                # Extract any useful info from config
                if isinstance(data, dict):
                    if "hostname" in data:
                        info["hostname"] = data["hostname"]
                    # Get instance name from sunshine_name config
                    if "sunshine_name" in data:
                        info["instance_name"] = data["sunshine_name"]
                    if "env" in data and isinstance(data["env"], dict):
                        env = data["env"]
                        if "COMPUTERNAME" in env:
                            info["hostname"] = env["COMPUTERNAME"]
            except:
                continue

    except Exception as e:
        pass

    # Fallback: DNS lookup for hostname
    if not info["hostname"]:
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            info["hostname"] = hostname.split(".")[0].upper()
        except:
            info["hostname"] = f"UNKNOWN-{ip.split('.')[-1]}"

    # Fix generic "HOST" hostname with actual hostname
    if info["hostname"] == "HOST":
        local_hostname = socket.gethostname().upper()
        info["hostname"] = local_hostname

    # If local, also get hardware specs
    if is_local:
        local_info = get_local_machine_info()
        info["gpu"] = local_info.get("gpu")
        info["ram"] = local_info.get("ram")
        info["os"] = local_info.get("os")
        info["cpu"] = local_info.get("cpu")

    return info


def scan_single_ip(ip: str) -> dict[str, Any] | None:
    """Scan a single IP for Apollo servers on all configured ports.

    Checks all configured Apollo ports and retrieves machine info from each.

    Args:
        ip: IP address to scan.

    Returns:
        Workstation dict with apollo_instances if any Apollo found, None otherwise.
    """
    # Check all configured ports
    open_ports = check_apollo_ports(ip)

    if not open_ports:
        return None

    # Gather info from the first responding port for machine-level data
    first_info = get_machine_info_apollo(ip, open_ports[0])

    # Try WMI for hardware specs if not already populated
    if not first_info.get("gpu") or not first_info.get("ram"):
        wmi_info = get_machine_info_wmi(ip)
        for key, value in wmi_info.items():
            if value and not first_info.get(key):
                first_info[key] = value

    # Build apollo_instances array with info from each port
    apollo_instances = []
    for port in open_ports:
        port_info = (
            get_machine_info_apollo(ip, port)
            if port != open_ports[0]
            else first_info
        )
        instance_name = port_info.get("instance_name") or f"Display ({port})"
        apollo_instances.append(
            {
                "port": port,
                "name": instance_name,
                "apps": port_info.get("apps", []),
            }
        )

    return {
        "ip": ip,
        "hostname": first_info.get("hostname", f"UNKNOWN-{ip.split('.')[-1]}"),
        "apollo_instances": apollo_instances,
        "gpu": first_info.get("gpu"),
        "ram": first_info.get("ram"),
        "os": first_info.get("os", "Windows"),
        "cpu": first_info.get("cpu"),
    }


@app.route("/")
def index() -> str:
    """Render the main dashboard page.

    Returns:
        Rendered HTML template with workstations and site config.
    """
    data = load_workstations()
    site = get_site_config()
    network = get_network_config()
    apollo = {
        "port": get_primary_apollo_port(),
    }

    workstations = data["workstations"]

    # Extract unique groups (sorted, with empty/None last)
    groups = sorted(
        set(ws.get("group", "") for ws in workstations if ws.get("group"))
    )

    # Group workstations by group
    grouped_workstations = {}
    has_groups = any(ws.get("group") for ws in workstations)

    if has_groups:
        # First add named groups in order
        for group in groups:
            grouped_workstations[group] = [
                ws for ws in workstations if ws.get("group") == group
            ]
        # Then add ungrouped (empty/None group) at the end
        ungrouped = [ws for ws in workstations if not ws.get("group")]
        if ungrouped:
            grouped_workstations[""] = ungrouped

    # Get server's local IPs for "this server" indicator
    try:
        server_ips = socket.gethostbyname_ex(socket.gethostname())[2]
    except Exception:
        server_ips = []

    # Load group icons
    groups_data = load_groups()
    group_icons = groups_data.get("groups", {})

    return render_template(
        "index.html",
        workstations=workstations,
        grouped_workstations=grouped_workstations if has_groups else None,
        groups=groups,
        group_icons=group_icons,
        site=site,
        network=network,
        apollo=apollo,
        server_ips=server_ips,
    )


@app.route("/api/workstations", methods=["GET"])
def get_workstations() -> Response:
    """Get all workstations.

    Returns:
        JSON response with workstations list.
    """
    return jsonify(load_workstations())


@app.route("/api/workstations/<ws_id>", methods=["PUT"])
def update_workstation(ws_id: str) -> tuple[Response, int] | Response:
    """Update a workstation.

    Args:
        ws_id: Workstation ID to update.

    Returns:
        JSON response with success status. 404 if not found.
    """
    data = load_workstations()
    for i, ws in enumerate(data["workstations"]):
        if ws["id"] == ws_id:
            data["workstations"][i].update(request.json)
            save_workstations(data)
            return jsonify({"success": True})
    return jsonify({"success": False, "error": "Not found"}), 404


@app.route("/api/workstations/<ws_id>", methods=["DELETE"])
def delete_workstation(ws_id: str) -> Response:
    """Delete a workstation.

    Args:
        ws_id: Workstation ID to delete.

    Returns:
        JSON response with success status.
    """
    data = load_workstations()
    data["workstations"] = [
        ws for ws in data["workstations"] if ws["id"] != ws_id
    ]
    save_workstations(data)
    return jsonify({"success": True})


@app.route("/api/groups", methods=["GET"])
def get_groups() -> Response:
    """Get all group metadata.

    Returns:
        JSON response with groups data.
    """
    return jsonify(load_groups())


@app.route("/api/groups/<group_name>", methods=["PUT"])
def update_group(group_name: str) -> Response:
    """Update a group's metadata (icon, etc.).

    Args:
        group_name: Name of the group to update.

    Returns:
        JSON response with success status.
    """
    data = load_groups()
    if "groups" not in data:
        data["groups"] = {}

    if group_name not in data["groups"]:
        data["groups"][group_name] = {}

    data["groups"][group_name].update(request.json)
    save_groups(data)
    return jsonify({"success": True})


@app.route("/api/discover", methods=["POST"])
def discover_apollo_servers() -> Response:
    """Scan network for Apollo servers.

    Accepts optional JSON body with subnet, start, and end parameters.
    Uses parallel scanning for speed.

    Returns:
        JSON response with discovered servers, count, and scanned IPs.
    """
    req_data = request.json or {}
    network_config = get_network_config()

    # Get values with fallback to defaults, handling None/empty
    subnet = req_data.get("subnet") or network_config["subnet"]
    start_ip = req_data.get("start")
    end_ip = req_data.get("end")

    # Ensure integers with defaults
    try:
        start_ip = (
            int(start_ip)
            if start_ip is not None
            else network_config["scan_start"]
        )
    except (ValueError, TypeError):
        start_ip = network_config["scan_start"]

    try:
        end_ip = (
            int(end_ip) if end_ip is not None else network_config["scan_end"]
        )
    except (ValueError, TypeError):
        end_ip = network_config["scan_end"]

    # Validate range
    start_ip = max(1, min(254, start_ip))
    end_ip = max(1, min(254, end_ip))
    if start_ip > end_ip:
        start_ip, end_ip = end_ip, start_ip

    discovered = []
    ips_to_scan = [f"{subnet}.{i}" for i in range(start_ip, end_ip + 1)]

    # Parallel scanning for speed
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = {
            executor.submit(scan_single_ip, ip): ip for ip in ips_to_scan
        }
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                discovered.append(result)

    # Sort by IP
    discovered.sort(key=lambda x: [int(p) for p in x["ip"].split(".")])

    return jsonify(
        {
            "success": True,
            "discovered": discovered,
            "count": len(discovered),
            "scanned": len(ips_to_scan),
        }
    )


@app.route("/api/probe/<ip>")
def probe_host(ip: str) -> Response:
    """Probe a single host for Apollo instances and get detailed info.

    Checks all configured Apollo ports and retrieves hardware info via
    Apollo API and WMI/WinRM.

    Args:
        ip: IP address to probe.

    Returns:
        JSON response with apollo_online status, apollo_instances, and machine info.
    """
    result = {
        "ip": ip,
        "apollo_online": False,
        "hostname": None,
        "apollo_instances": [],
        "gpu": None,
        "ram": None,
        "os": None,
    }

    # Check all configured Apollo ports
    open_ports = check_apollo_ports(ip)

    if open_ports:
        result["apollo_online"] = True

        # Get info from first responding port for machine-level data
        first_info = get_machine_info_apollo(ip, open_ports[0])
        result["hostname"] = first_info.get("hostname")
        result["gpu"] = first_info.get("gpu")
        result["ram"] = first_info.get("ram")
        result["os"] = first_info.get("os")
        result["cpu"] = first_info.get("cpu")

        # Build apollo_instances array
        for port in open_ports:
            port_info = (
                get_machine_info_apollo(ip, port)
                if port != open_ports[0]
                else first_info
            )
            instance_name = (
                port_info.get("instance_name") or f"Display ({port})"
            )
            result["apollo_instances"].append(
                {
                    "port": port,
                    "name": instance_name,
                    "apps": port_info.get("apps", []),
                }
            )

        # Try WMI for more details
        wmi_info = get_machine_info_wmi(ip)
        for key, value in wmi_info.items():
            if value and not result.get(key):
                result[key] = value

    return jsonify(result)


@app.route("/api/import-discovered", methods=["POST"])
def import_discovered() -> Response:
    """Import discovered workstations.

    Accepts JSON body with workstations array. Skips duplicates based on IP.

    Returns:
        JSON response with imported count and skipped count.
    """
    req_data = request.json or {}
    discovered = req_data.get("workstations", [])

    data = load_workstations()
    existing_ips = {ws["ip"] for ws in data["workstations"]}

    imported = 0
    for ws in discovered:
        if ws["ip"] not in existing_ips:
            ws["id"] = str(datetime.now().timestamp()).replace(".", "") + str(
                imported
            )
            ws["created"] = datetime.now().isoformat()
            ws["name"] = ws.get(
                "hostname", ws.get("name", f"WS-{ws['ip'].split('.')[-1]}")
            )
            data["workstations"].append(ws)
            imported += 1

    save_workstations(data)

    return jsonify(
        {
            "success": True,
            "imported": imported,
            "skipped": len(discovered) - imported,
        }
    )


@app.route("/api/clients/<ip>")
def get_workstation_clients(ip: str) -> Response:
    """Get paired Moonlight clients for a workstation.

    Args:
        ip: IP address of the Apollo server.

    Returns:
        JSON response with clients list and count.
    """
    clients = get_paired_clients(ip)
    return jsonify(
        {"success": True, "ip": ip, "clients": clients, "count": len(clients)}
    )


@app.route("/api/ping/<ip>")
def ping_host(ip: str) -> Response:
    """Check if a host is online via ICMP ping.

    Args:
        ip: IP address to ping.

    Returns:
        JSON response with online status and latency in seconds.
    """
    try:
        import ping3

        result = ping3.ping(ip, timeout=1)
        return jsonify({"online": result is not None, "latency": result})
    except Exception as e:
        return jsonify({"online": False, "error": str(e)})


@app.route("/download/moonlight-handler.reg")
def download_protocol_handler() -> Response:
    """Generate and download the Moonlight protocol handler .reg file.

    Creates a Windows registry file that registers the moonlight://
    URL protocol. The handler is self-contained with embedded PowerShell.
    Supports optional port parameter for multi-instance Apollo setups.

    URL formats supported:
    - moonlight://connect/{IP}?app={App} (default port)
    - moonlight://connect/{IP}?port={PORT}&app={App} (specific port)

    Returns:
        Response with .reg file content for download.
    """
    # Inline PowerShell script that handles optional port parameter
    # URL format: moonlight://connect/{IP}?port={PORT}&app={App} or moonlight://connect/{IP}?app={App}
    ps_script = (
        "$url = $args[0]; "
        "if ($url -match 'moonlight://connect/([^?]+)\\?(?:port=(\\d+)&)?app=(.+)') { "
        "$ip = $matches[1]; $port = $matches[2]; $app = [uri]::UnescapeDataString($matches[3]); "
        '$target = if ($port) { "${ip}:${port}" } else { $ip }; '
        "& 'C:\\Program Files\\Moonlight Game Streaming\\Moonlight.exe' stream $target $app "
        "}"
    )

    # Build the command line - escape for .reg file format
    command = f'powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -Command "{ps_script}" "%1"'
    # Escape backslashes for .reg format
    command_escaped = command.replace("\\", "\\\\")

    reg_content = f"""Windows Registry Editor Version 5.00

[HKEY_CURRENT_USER\\Software\\Classes\\moonlight]
@="URL:Moonlight Protocol"
"URL Protocol"=""

[HKEY_CURRENT_USER\\Software\\Classes\\moonlight\\shell]

[HKEY_CURRENT_USER\\Software\\Classes\\moonlight\\shell\\open]

[HKEY_CURRENT_USER\\Software\\Classes\\moonlight\\shell\\open\\command]
@="{command_escaped}"
"""

    return Response(
        reg_content,
        mimetype="application/x-ms-regedit",
        headers={
            "Content-Disposition": "attachment; filename=moonlight-handler.reg"
        },
    )


@app.route("/download/moonlight-handler-uninstall.reg")
def download_protocol_handler_uninstall() -> Response:
    """Generate and download a .reg file to uninstall the Moonlight protocol handlers.

    Creates a Windows registry file that removes the moonlight:// and
    moonlight-dual:// URL protocol registrations.

    Returns:
        Response with .reg file content for download.
    """
    reg_content = """Windows Registry Editor Version 5.00

[-HKEY_CURRENT_USER\\Software\\Classes\\moonlight]

[-HKEY_CURRENT_USER\\Software\\Classes\\moonlight-dual]
"""

    return Response(
        reg_content,
        mimetype="application/x-ms-regedit",
        headers={
            "Content-Disposition": "attachment; filename=moonlight-handler-uninstall.reg"
        },
    )


if __name__ == "__main__":
    # For development only - use waitress for production
    app.run(debug=True, host="0.0.0.0", port=get_server_port())
