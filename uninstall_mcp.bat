@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" engine\register_mcp.py --remove
echo You can now delete the .venv folder to remove all installed packages.
pause
