@echo off
setlocal
cd /d "%~dp0"
echo === Claude DnD setup ===
set "PY=python"
where py >nul 2>nul && set "PY=py -3"
if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment in .venv ...
  %PY% -m venv .venv
  if errorlevel 1 goto :err
)
".venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" || (echo Python 3.10 or newer is required. & goto :err)
if errorlevel 1 goto :err
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r engine\requirements.txt
if errorlevel 1 goto :err
".venv\Scripts\python.exe" engine\register_mcp.py
if errorlevel 1 goto :err
echo.
echo Setup complete. Fully quit and reopen the Claude desktop app so it loads the claude-dnd MCP server.
pause
exit /b 0
:err
echo.
echo Setup FAILED - see messages above.
pause
exit /b 1
