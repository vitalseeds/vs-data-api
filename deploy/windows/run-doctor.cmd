@echo off
rem Run vsdata-doctor from this checkout (developer settings from .env if there is no config.ini).
rem Double-click it, or run it from any folder.
rem
rem On the VM the checkout is the Mac's shared folder, whose .venv holds macOS binaries, so keep
rem Windows' environment elsewhere (set UV_PROJECT_ENVIRONMENT yourself to choose another place).
if not defined UV_PROJECT_ENVIRONMENT set "UV_PROJECT_ENVIRONMENT=%LOCALAPPDATA%\vsdata-doctor-venv"
cd /d "%~dp0\..\.."
uv run vsdata-doctor %*
