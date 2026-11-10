@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
 start "" ".venv\Scripts\pythonw.exe" "launch_hidden.pyw"
) else (
 echo Bitte zuerst Setup_ToolForge.cmd ausfuehren.
 pause
)
