@echo off
rem Double-click to update VS Data API to the latest GitHub release.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0update.ps1" %*
