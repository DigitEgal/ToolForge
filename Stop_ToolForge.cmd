@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
 ".venv\Scripts\python.exe" "stop_toolforge.py"
) else (
 python "stop_toolforge.py"
)
if /i not "%~1"=="/quiet" pause
