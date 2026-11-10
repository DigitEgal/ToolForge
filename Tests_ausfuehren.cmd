@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -m pytest backend/tests tests -q
) else (
    python -m pytest backend/tests tests -q
)
echo.
pause
endlocal
