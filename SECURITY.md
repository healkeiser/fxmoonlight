# Security Policy

## Credentials Handling

This application handles sensitive credentials for WinRM and Apollo access. Follow these best practices:

### ✅ Recommended: Environment Variables

Store passwords in environment variables instead of `config.json`:

```json
{
  "credentials": {
    "winrm_user": "${WINRM_USER:-Administrator}",
    "winrm_password": "${WINRM_PASSWORD}",
    "apollo_user": "${APOLLO_USER}",
    "apollo_password": "${APOLLO_PASSWORD}"
  }
}
```

Set environment variables securely:

```powershell
# User level (persisted, visible only to current user)
[Environment]::SetEnvironmentVariable("WINRM_PASSWORD", "your-password", "User")

# For Windows Service (NSSM)
nssm set MoonlightDashboard AppEnvironmentExtra WINRM_PASSWORD=secret APOLLO_PASSWORD=secret
```

### ❌ Avoid

- Committing `config.json` with real passwords to git
- Using weak or default passwords
- Sharing credentials in plain text

## Network Security

- The dashboard binds to `0.0.0.0` by default (all interfaces)
- Consider using a reverse proxy (nginx, Caddy) with HTTPS for production
- Firewall rules should limit access to the dashboard port (default: `5000`)
- WinRM (port `5985`) and Apollo (ports `47990`, `48989`, `47980`, `46990`, or whichever ports you configure) traffic should be restricted to trusted networks

## Files

| File | Sensitivity | Notes |
|------|-------------|-------|
| `config.json` | 🔴 High | May contain passwords - gitignored |
| `data.json` | 🟡 Medium | Contains IP addresses - gitignored |
| `config.example.json` | 🟢 Low | Template only, no real credentials |

## Reporting Vulnerabilities

If you discover a security vulnerability, please open a private issue or contact [me](https://github.com/healkeiser) directly rather than disclosing publicly.
