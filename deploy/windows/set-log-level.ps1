# set-log-level.ps1
# Sets vs_data_logging_level in config.ini and restarts the VS Data API service.
#
# Normally used via debug-logging.cmd (DEBUG) and normal-logging.cmd (INFO).
# Logs: C:\Program Files\VSData\logs\stderr.log and stdout.log
#
# Usage:
#   .\set-log-level.ps1 -Level DEBUG
#   .\set-log-level.ps1 -Level INFO

param(
    [Parameter(Mandatory)][ValidateSet("DEBUG", "INFO", "WARNING", "ERROR")][string]$Level,
    [string]$ServiceName = "VSDataAPI",
    [string]$ConfigPath = (Join-Path $env:APPDATA "VSData\config.ini")
)

$ErrorActionPreference = "Stop"

# Re-launch elevated: restarting a service needs admin. $env:APPDATA is the
# current user's, so pass the resolved config path through.
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Requesting administrator rights..."
    $argList = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`"",
        "-Level", $Level, "-ServiceName", $ServiceName, "-ConfigPath", "`"$ConfigPath`"")
    Start-Process powershell -Verb RunAs -ArgumentList $argList
    exit
}

if (-not (Test-Path $ConfigPath)) {
    Write-Host "Config file not found: $ConfigPath" -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

$lines = [System.Collections.Generic.List[string]](Get-Content $ConfigPath)
$keyLine = "vs_data_logging_level = $Level"
$inSection = $false
$sectionAt = -1
$keyAt = -1
for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match '^\s*\[(.+)\]\s*$') {
        $inSection = ($Matches[1] -eq "logging")
        if ($inSection) { $sectionAt = $i }
    }
    elseif ($inSection -and $lines[$i] -match '^\s*vs_data_logging_level\s*=') {
        $keyAt = $i
    }
}

if ($keyAt -ge 0) { $lines[$keyAt] = $keyLine }
elseif ($sectionAt -ge 0) { $lines.Insert($sectionAt + 1, $keyLine) }
else { $lines.Add(""); $lines.Add("[logging]"); $lines.Add($keyLine) }

Copy-Item $ConfigPath "$ConfigPath.bak" -Force
Set-Content -Path $ConfigPath -Value $lines
Write-Host "Set logging level to $Level in $ConfigPath (backup: config.ini.bak)"

Restart-Service -Name $ServiceName -Force
Write-Host "Restarted $ServiceName"
Write-Host "Logs: C:\Program Files\VSData\logs\stderr.log"
Read-Host "Press Enter to close"
