@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" "%~dp0start_toolforge_pilot.py"
) else (
    python "%~dp0start_toolforge_pilot.py"
)
if errorlevel 1 (
    echo.
    echo Start fehlgeschlagen. Fehlermeldung siehe oben.
    echo Fuer die Ersteinrichtung: Setup_ToolForge.cmd ausfuehren.
    pause
)
endlocal
