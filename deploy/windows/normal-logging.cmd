@echo off
rem Double-click to restore normal (INFO) logging and restart the service.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0set-log-level.ps1" -Level INFO %*
