---

## Installation and Configuration

### Install on macOS

#### 1. Copy the executable

```bash
# Create installation directory
sudo mkdir -p /usr/local/bin
sudo mkdir -p /usr/local/var/log

# Copy executable (or symlink)
sudo cp dist/vsdata-server/vsdata-server /usr/local/bin/
sudo chmod +x /usr/local/bin/vsdata-server
```

#### 2. Create configuration file

```bash
# Create config directory
mkdir -p ~/Library/Application\ Support/VSData

# Copy and edit config template
cp config/config.ini.example ~/Library/Application\ Support/VSData/config.ini
```

Edit `~/Library/Application Support/VSData/config.ini` with your credentials:

```ini
[vsdata]
fm_connection_string = Driver={FileMaker ODBC};Server=localhost;Database=vs_db;UID=vsdata;PWD=yourpassword;
fm_link_connection_string = Driver={FileMaker ODBC};Server=localhost;Database=wc_link;UID=vsdata;PWD=yourpassword;
wc_url = https://vitalseeds.co.uk
wc_key = ck_your_key_here
wc_secret = cs_your_secret_here

[server]
host = 0.0.0.0
port = 8432
```

#### 3. Test the executable

```bash
# Run directly to test
/usr/local/bin/vsdata-server

# Should show:
# ==================================================
# VS Data API Server
# ==================================================
# Host: 0.0.0.0
# Port: 8432
# ...
```

Press `Ctrl+C` to stop.

#### 4. Install as LaunchAgent (auto-start)

```bash
# Copy LaunchAgent plist
cp deploy/macos/com.vitalseeds.vsdata-api.plist ~/Library/LaunchAgents/

# Load the agent
launchctl load ~/Library/LaunchAgents/com.vitalseeds.vsdata-api.plist

# Check status
launchctl list | grep vsdata
```

**LaunchAgent management:**

```bash
# Start
launchctl start com.vitalseeds.vsdata-api

# Stop
launchctl stop com.vitalseeds.vsdata-api

# Unload (disable auto-start)
launchctl unload ~/Library/LaunchAgents/com.vitalseeds.vsdata-api.plist

# View logs
tail -f /usr/local/var/log/vsdata-api.log
```

---

### Install on Windows 11

#### 1. Install NSSM

Download NSSM from https://nssm.cc/download and extract to a location in your PATH (e.g., `C:\Program Files\nssm\`).

#### 2. Copy the executable

```powershell
# Create installation directory
New-Item -ItemType Directory -Path "C:\Program Files\VSData" -Force

# Copy all files from the build
Copy-Item -Path "dist\vsdata-server\*" -Destination "C:\Program Files\VSData\" -Recurse
```

#### 3. Create configuration file

```powershell
# Create config directory
New-Item -ItemType Directory -Path "$env:APPDATA\VSData" -Force

# Copy config template
Copy-Item "config\config.ini.example" "$env:APPDATA\VSData\config.ini"

# Open in notepad to edit
notepad "$env:APPDATA\VSData\config.ini"
```

Edit with your credentials (same format as macOS above).

#### 4. Test the executable

```powershell
# Run directly to test
& "C:\Program Files\VSData\vsdata-server.exe"

# Should show server startup info
# Press Ctrl+C to stop
```

#### 5. Install as Windows Service

Run PowerShell as Administrator:

```powershell
# Navigate to the repository
cd path\to\vs-data-api

# Run the installer script
.\deploy\windows\install-service.ps1
```

Or install manually:

```powershell
# Install service
nssm install VSDataAPI "C:\Program Files\VSData\vsdata-server.exe"

# Configure service
nssm set VSDataAPI DisplayName "VS Data API"
nssm set VSDataAPI Description "Vital Seeds Data API Server"
nssm set VSDataAPI Start SERVICE_AUTO_START
nssm set VSDataAPI AppDirectory "C:\Program Files\VSData"

# Configure logging
nssm set VSDataAPI AppStdout "C:\Program Files\VSData\logs\stdout.log"
nssm set VSDataAPI AppStderr "C:\Program Files\VSData\logs\stderr.log"

# Configure restart behavior
nssm set VSDataAPI AppExit Default Restart
nssm set VSDataAPI AppExit 0 Exit
nssm set VSDataAPI AppExit 1 Exit
nssm set VSDataAPI AppRestartDelay 5000

# Start the service
Start-Service VSDataAPI
```

**Service management:**

```powershell
# Check status
Get-Service VSDataAPI

# Start/Stop/Restart
Start-Service VSDataAPI
Stop-Service VSDataAPI
Restart-Service VSDataAPI

# View logs
Get-Content "C:\Program Files\VSData\logs\stdout.log" -Tail 50

# Uninstall
Stop-Service VSDataAPI
nssm remove VSDataAPI confirm
```

#### 6. Configure Windows Firewall

```powershell
# Allow incoming connections on port 8432
New-NetFirewallRule -DisplayName "VS Data API" -Direction Inbound -Protocol TCP -LocalPort 8432 -Action Allow
```

---

## Testing the Installation

After installing and starting the service, verify everything is working correctly.

### 1. Check the Server is Running

**macOS:**
```bash
# Check process
ps aux | grep vsdata-server

# Check LaunchAgent status
launchctl list | grep vsdata
```

**Windows:**
```powershell
# Check service status
Get-Service VSDataAPI

# Should show: Running
```

### 2. Test Local API Response

```bash
# Basic health check
curl http://localhost:8432/

# Expected response:
# {"message":"VS Data API running"}
```

**Windows (PowerShell):**
```powershell
Invoke-WebRequest -Uri "http://localhost:8432/" | Select-Object -ExpandProperty Content
```

### 3. Test from Another Machine on the Network

From a different computer on the same LAN (replace IP with your server's address):

```bash
curl http://192.168.1.100:8432/
```

If this fails but local access works, check your firewall settings.

### 4. Test FileMaker Connection

Call an endpoint that queries FileMaker to verify ODBC connectivity:

```bash
# This endpoint requires FileMaker to be running with ODBC enabled
curl http://localhost:8432/batch/awaiting_upload
```

If FileMaker is running and configured correctly, you should receive JSON data (or an empty array `[]` if no batches are waiting).

### 5. Test WooCommerce Connection

```bash
# Test an endpoint that queries WooCommerce
curl http://localhost:8432/orders/recent
```

### 6. Check Logs for Errors

**macOS:**
```bash
tail -50 /usr/local/var/log/vsdata-api.log
tail -50 /usr/local/var/log/vsdata-api.error.log
```

**Windows:**
```powershell
Get-Content "C:\Program Files\VSData\logs\stdout.log" -Tail 50
Get-Content "C:\Program Files\VSData\logs\stderr.log" -Tail 50
```

### Quick Test Checklist

| Test | Command | Expected Result |
|------|---------|-----------------|
| Server running | `curl http://localhost:8432/` | `{"message":"VS Data API running"}` |
| LAN access | `curl http://<server-ip>:8432/` | Same as above |
| FileMaker ODBC | `curl http://localhost:8432/batch/awaiting_upload` | JSON array (may be empty) |
| Service status | `Get-Service VSDataAPI` (Win) | Status: Running |

---

## Configuration Reference

### Config File Location

| Platform | Path |
|----------|------|
| Windows | `%APPDATA%\VSData\config.ini` |
| macOS | `~/Library/Application Support/VSData/config.ini` |
| Linux | `~/.config/vsdata/config.ini` |

### Configuration Priority

1. Environment variables (highest priority)
2. Config file values
3. Built-in defaults (lowest priority)

### Required Settings

| Setting | Environment Variable | Description |
|---------|---------------------|-------------|
| FileMaker connection | `VSDATA_FM_CONNECTION_STRING` | ODBC connection string for main database |
| FileMaker link connection | `VSDATA_FM_LINK_CONNECTION_STRING` | ODBC connection string for link database |
| WooCommerce URL | `VSDATA_WC_URL` | Your WooCommerce store URL |
| WooCommerce key | `VSDATA_WC_KEY` | WooCommerce API consumer key |
| WooCommerce secret | `VSDATA_WC_SECRET` | WooCommerce API consumer secret |

### Optional Settings

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| Host | `VSDATA_HOST` | `0.0.0.0` | Network interface to bind |
| Port | `VSDATA_PORT` | `8432` | Server port |
| SSL cert | `SSL_CERTFILE` | (none) | Path to SSL certificate |
| SSL key | `SSL_KEYFILE` | (none) | Path to SSL private key |
| Log level | `VS_DATA_LOGGING_LEVEL` | `INFO` | DEBUG, INFO, WARNING, ERROR |

### Exit Codes

| Code | Meaning | Service Action |
|------|---------|----------------|
| 0 | Clean shutdown | Don't restart |
| 1 | Configuration error | Don't restart (needs manual fix) |
| 2 | Runtime error | Auto-restart |

---

## Network Access

### Verify Local Access

```bash
# From the server machine
curl http://localhost:8432/
# Should return: {"message":"VS Data API running"}
```

### Verify LAN Access

From another machine on the same network:

```bash
# Replace with your server's IP address
curl http://192.168.1.100:8432/
```

### Find Your Server's IP Address

**macOS:**
```bash
ipconfig getifaddr en0
```

**Windows:**
```powershell
(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" }).IPAddress
```

### FileMaker Configuration

In your FileMaker scripts, use the server's LAN IP:

```
Set Variable [ $URL ; Value: "http://192.168.1.100:8432/your-endpoint" ]
Insert from URL [ Select ; With dialog: Off ; Target: $RESPONSE ; $URL ]
```

---

## Troubleshooting

### Configuration Errors

If the server exits immediately with code 1, check the logs for missing configuration:

```
==================================================
CONFIGURATION ERROR
==================================================
Missing required configuration:
  - VSDATA_FM_CONNECTION_STRING
  ...
```

Ensure all required settings are in your config file or environment.

### FileMaker ODBC Connection

**macOS:**
- Ensure libiodbc is installed: `brew install libiodbc`
- Verify driver is registered in ODBC Manager
- Check FileMaker has ODBC sharing enabled

**Windows:**
- Install FileMaker ODBC driver from Claris
- Verify connection string uses correct driver name: `Driver={FileMaker ODBC}`

### Service Won't Start

**Windows:**
```powershell
# Check service status
nssm status VSDataAPI

# View error logs
Get-Content "C:\Program Files\VSData\logs\stderr.log" -Tail 100
```

**macOS:**
```bash
# Check if running
launchctl list | grep vsdata

# View error logs
cat /usr/local/var/log/vsdata-api.error.log
```

### Port Already in Use

If port 8432 is already in use, either:
1. Change the port in config.ini
2. Find and stop the conflicting process:

```bash
# macOS/Linux
lsof -i :8432

# Windows
netstat -ano | findstr :8432
```

### Firewall Blocking Access

**Windows:**
```powershell
# Check if rule exists
Get-NetFirewallRule -DisplayName "VS Data API"

# Add rule if missing
New-NetFirewallRule -DisplayName "VS Data API" -Direction Inbound -Protocol TCP -LocalPort 8432 -Action Allow
```

**macOS:**
- Check System Preferences → Security & Privacy → Firewall → Firewall Options
- Ensure the application is allowed to receive incoming connections
