@echo off
cd /d "%~dp0"
python setup_toolforge.py
if errorlevel 1 echo Einrichtung fehlgeschlagen. Fehlermeldung siehe oben.
pause
