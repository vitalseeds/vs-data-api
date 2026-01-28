# install-service.ps1
# Installs VS Data API as a Windows service using NSSM
#
# Prerequisites:
#   1. NSSM must be installed (https://nssm.cc/download)
#   2. FileMaker ODBC driver must be installed
#   3. vsdata-server.exe must be built and placed in install directory
#
# Usage:
#   .\install-service.ps1
#   .\install-service.ps1 -InstallPath "D:\Apps\VSData"

param(
    [string]$InstallPath = "C:\Program Files\VSData",
    [string]$ServiceName = "VSDataAPI",
    [string]$ServiceDisplayName = "VS Data API",
    [string]$ServiceDescription = "Vital Seeds Data API - Provides HTTP API for FileMaker and WooCommerce integration"
)

# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script must be run as Administrator"
    exit 1
}

# Verify NSSM is available
$nssm = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssm) {
    Write-Error "NSSM not found. Please install NSSM from https://nssm.cc/download and add to PATH"
    exit 1
}

# Verify executable exists
$exePath = Join-Path $InstallPath "vsdata-server.exe"
if (-not (Test-Path $exePath)) {
    Write-Error "Executable not found at $exePath"
    Write-Host "Please copy the built executable to $InstallPath first"
    exit 1
}

# Create log directory
$logPath = Join-Path $InstallPath "logs"
if (-not (Test-Path $logPath)) {
    New-Item -ItemType Directory -Path $logPath -Force | Out-Null
    Write-Host "Created log directory: $logPath"
}

# Stop and remove existing service if present
$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host "Stopping existing service..."
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Host "Removing existing service..."
    & nssm remove $ServiceName confirm
    Start-Sleep -Seconds 1
}

# Install the service
Write-Host "Installing service $ServiceName..."
& nssm install $ServiceName $exePath

# Configure service settings
Write-Host "Configuring service settings..."
& nssm set $ServiceName DisplayName $ServiceDisplayName
& nssm set $ServiceName Description $ServiceDescription
& nssm set $ServiceName Start SERVICE_AUTO_START
& nssm set $ServiceName AppDirectory $InstallPath

# Configure logging
Write-Host "Configuring logging..."
& nssm set $ServiceName AppStdout (Join-Path $logPath "stdout.log")
& nssm set $ServiceName AppStderr (Join-Path $logPath "stderr.log")
& nssm set $ServiceName AppStdoutCreationDisposition 4
& nssm set $ServiceName AppStderrCreationDisposition 4
& nssm set $ServiceName AppRotateFiles 1
& nssm set $ServiceName AppRotateOnline 1
& nssm set $ServiceName AppRotateBytes 10485760  # 10MB

# Configure exit code handling for automatic restart
# Exit 0 = clean shutdown, don't restart
# Exit 1 = config error, don't restart (needs manual fix)
# Exit 2+ = runtime error, restart
Write-Host "Configuring restart behavior..."
& nssm set $ServiceName AppExit Default Restart
& nssm set $ServiceName AppExit 0 Exit
& nssm set $ServiceName AppExit 1 Exit
& nssm set $ServiceName AppRestartDelay 5000  # 5 second delay before restart

Write-Host ""
Write-Host "=" * 60
Write-Host "Service installed successfully!"
Write-Host "=" * 60
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Create config file:"
Write-Host "     New-Item -ItemType Directory `"$env:APPDATA\VSData`" -Force"
Write-Host "     Copy config\config.ini.example to $env:APPDATA\VSData\config.ini"
Write-Host "     Edit config.ini with your FileMaker and WooCommerce credentials"
Write-Host ""
Write-Host "  2. Start the service:"
Write-Host "     Start-Service $ServiceName"
Write-Host ""
Write-Host "  3. Check status:"
Write-Host "     Get-Service $ServiceName"
Write-Host "     nssm status $ServiceName"
Write-Host ""
Write-Host "  4. View logs:"
Write-Host "     Get-Content `"$logPath\stdout.log`" -Tail 50"
Write-Host ""
Write-Host "  5. Open firewall (if needed):"
Write-Host "     New-NetFirewallRule -DisplayName `"VS Data API`" -Direction Inbound -Protocol TCP -LocalPort 8432 -Action Allow"
Write-Host ""
Write-Host "Service management commands:"
Write-Host "  Start:   Start-Service $ServiceName"
Write-Host "  Stop:    Stop-Service $ServiceName"
Write-Host "  Restart: Restart-Service $ServiceName"
Write-Host "  Remove:  nssm remove $ServiceName confirm"
