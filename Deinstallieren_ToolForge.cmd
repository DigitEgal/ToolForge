@echo off
cd /d "%~dp0"
echo ToolForge Pilot deinstallieren
echo Eigene Projektordner bleiben unveraendert.
echo.
where python >nul 2>nul
if not errorlevel 1 (
    python "uninstall_toolforge.py" %*
) else if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "uninstall_toolforge.py" %*
) else (
    echo Python wurde nicht gefunden. Bitte Python 3.11 oder neuer installieren.
)
echo.
pause
