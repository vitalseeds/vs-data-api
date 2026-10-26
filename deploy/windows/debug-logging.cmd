@echo off
rem Double-click to switch VS Data API to DEBUG logging and restart the service.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0set-log-level.ps1" -Level DEBUG %*
