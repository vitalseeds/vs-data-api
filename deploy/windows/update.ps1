# update.ps1
# Updates the installed VS Data API to the latest GitHub release.
#
# Steps: download latest vsdata-server.exe (and vsdata-doctor.exe) -> stop server
#        -> back up install -> replace exe -> start server -> health check
#        (rollback on failure) -> replace the doctor exe
#
# Handles the server running as a Windows service (NSSM), as a plain
# process, or not running at all.
#
# Usage (normally via update.cmd):
#   .\update.ps1
#   .\update.ps1 -Tag v3.1.0
#   .\update.ps1 -InstallPath "D:\Apps\VSData"

param(
    [string]$InstallPath = "C:\Program Files\VSData",
    [string]$ServiceName = "VSDataAPI",
    [string]$Repo = "vitalseeds/vs-data-api",
    [string]$Tag = "latest",
    [int]$Port = 8432,
    [int]$KeepBackups = 3
)

$ErrorActionPreference = "Stop"
$ExeName = "vsdata-server.exe"
$DoctorName = "vsdata-doctor.exe"
$ProcessName = [IO.Path]::GetFileNameWithoutExtension($ExeName)

# Re-launch elevated if needed (Program Files requires admin)
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Requesting administrator rights..."
    $argList = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`"",
        "-InstallPath", "`"$InstallPath`"", "-ServiceName", $ServiceName, "-Repo", $Repo,
        "-Tag", $Tag, "-Port", $Port, "-KeepBackups", $KeepBackups)
    Start-Process powershell -Verb RunAs -ArgumentList $argList
    exit
}

function Wait-ForHealth {
    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Seconds 2
        try {
            $r = Invoke-WebRequest -Uri "http://localhost:$Port/" -UseBasicParsing -TimeoutSec 3
            if ($r.StatusCode -eq 200) { return $true }
        } catch { }
    }
    return $false
}

function Stop-Server {
    if ($script:service) {
        Stop-Service -Name $ServiceName -Force
        $script:service.WaitForStatus("Stopped", [TimeSpan]::FromSeconds(30))
    }
    elseif ($script:process) {
        $script:process | Stop-Process -Force
        $script:process | Wait-Process -Timeout 30 -ErrorAction SilentlyContinue
    }
}

function Start-Server {
    if ($script:service) {
        Start-Service -Name $ServiceName
    }
    elseif ($script:process) {
        Start-Process -FilePath $exePath -WorkingDirectory $InstallPath
    }
}

try {
    $exePath = Join-Path $InstallPath $ExeName
    if (-not (Test-Path $exePath)) {
        throw "No existing install found at $exePath. Run the install steps first."
    }

    # Find the release
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $releaseUrl = if ($Tag -eq "latest") {
        "https://api.github.com/repos/$Repo/releases/latest"
    } else {
        "https://api.github.com/repos/$Repo/releases/tags/$Tag"
    }
    Write-Host "Checking $releaseUrl"
    $release = Invoke-RestMethod -Uri $releaseUrl -Headers @{ "User-Agent" = "vsdata-updater" }
    $asset = $release.assets | Where-Object { $_.name -eq $ExeName } | Select-Object -First 1
    if (-not $asset) { throw "Release $($release.tag_name) has no $ExeName asset." }

    $currentVersion = (Get-Item $exePath).VersionInfo.ProductVersion
    Write-Host "Installed: $currentVersion (file dated $((Get-Item $exePath).LastWriteTime))"
    Write-Host "Release:   $($release.tag_name)"

    # Download before touching the running install
    $tmp = Join-Path $env:TEMP "vsdata-update"
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    $newExe = Join-Path $tmp $ExeName
    Write-Host "Downloading $($asset.browser_download_url)"
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $newExe -UseBasicParsing
    if ((Get-Item $newExe).Length -lt 1MB) { throw "Downloaded file looks too small; aborting." }

    # The doctor ships in the same release. A missing or failed download only warns.
    $newDoctor = $null
    $doctorAsset = $release.assets | Where-Object { $_.name -eq $DoctorName } | Select-Object -First 1
    if ($doctorAsset) {
        try {
            $newDoctor = Join-Path $tmp $DoctorName
            Write-Host "Downloading $($doctorAsset.browser_download_url)"
            Invoke-WebRequest -Uri $doctorAsset.browser_download_url -OutFile $newDoctor -UseBasicParsing
            if ((Get-Item $newDoctor).Length -lt 1MB) { throw "Downloaded file looks too small." }
        } catch {
            Write-Warning "Could not download $DoctorName ($($_.Exception.Message)); it will not be updated."
            $newDoctor = $null
        }
    } else {
        Write-Warning "Release $($release.tag_name) has no $DoctorName asset; it will not be updated."
    }

    # What is running now?
    $script:service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    $script:process = $null
    if (-not $script:service) {
        $script:process = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue
    }
    if ($script:service) { Write-Host "Server mode: service '$ServiceName'" }
    elseif ($script:process) { Write-Host "Server mode: plain process" }
    else { Write-Host "Server is not running; it will not be started after the update." }
    $wasRunning = ($script:service -and $script:service.Status -eq "Running") -or $script:process

    # Stop, back up, replace
    Write-Host "Stopping server..."
    if ($wasRunning) { Stop-Server }

    $backupPath = "$InstallPath.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Write-Host "Backing up to $backupPath"
    Copy-Item -Path $InstallPath -Destination $backupPath -Recurse

    Write-Host "Replacing $ExeName"
    Copy-Item -Path $newExe -Destination $exePath -Force

    # Start and verify
    if ($wasRunning) {
        Write-Host "Starting server..."
        Start-Server
        if (-not (Wait-ForHealth)) {
            Write-Warning "Health check failed on http://localhost:$Port/ - rolling back."
            Stop-Server
            if (-not $script:service) {
                Get-Process -Name $ProcessName -ErrorAction SilentlyContinue | Stop-Process -Force
            }
            Copy-Item -Path (Join-Path $backupPath $ExeName) -Destination $exePath -Force
            Start-Server
            throw "Update to $($release.tag_name) failed; previous version restored (backup kept at $backupPath)."
        }
    }

    # Replace the doctor only after the server update is known good, so a rollback leaves a matching pair
    if ($newDoctor) {
        $doctorPath = Join-Path $InstallPath $DoctorName
        try {
            Copy-Item -Path $newDoctor -Destination $doctorPath -Force
            Write-Host "Replaced $DoctorName"
        } catch {
            Write-Warning "Could not replace $DoctorName (is it open?): $($_.Exception.Message)"
        }
    }

    # Prune old backups
    $parent = Split-Path $InstallPath -Parent
    $leaf = Split-Path $InstallPath -Leaf
    Get-ChildItem -Path $parent -Directory -Filter "$leaf.bak-*" |
        Sort-Object Name -Descending |
        Select-Object -Skip $KeepBackups |
        ForEach-Object { Write-Host "Removing old backup $($_.FullName)"; Remove-Item $_.FullName -Recurse -Force }

    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host ""
    Write-Host "Updated to $($release.tag_name) successfully." -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host "UPDATE FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Read-Host "Press Enter to close"
