@REM This command can be put in startup folder to trigger fastapi server on startup if neccessary
@REM Normally run.ps1 will be run directly from Task scheduler instead

@REM Start-Sleep -Seconds 1.5
@REM Get-ChildItem Env:
PowerShell -Command "Set-ExecutionPolicy Unrestricted" >> "%TEMP%\StartupLog.txt" 2>&1
powershell -Command "& '%VSDATA_API_ROOT%\run.ps1'"