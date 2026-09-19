@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" ( echo Run setup.bat first. & pause & exit /b 1 )
if not exist "config.json" ".venv\Scripts\python.exe" engine\tools\init_config.py
".venv\Scripts\python.exe" engine\ui_server.py
pause
