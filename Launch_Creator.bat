@echo off
REM Disney Infinity Creator launcher. Installs the Python dependencies (run.ps1) when they are missing or incomplete.
cd /d "%~dp0"
set PY=.venv\Scripts\python.exe
if exist "%PY%" "%PY%" -c "import customtkinter, moderngl, numpy, PIL, trimesh, scipy, cryptography" 2>nul
if not exist "%PY%" goto setup
if errorlevel 1 goto setup
goto run
:setup
echo Installing Python dependencies (first launch or interrupted install)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" -SetupOnly
if errorlevel 1 (
  echo.
  echo Setup failed. Python 3.12+ must be installed and on PATH, with an internet connection.
  pause
  exit /b 1
)
:run
"%PY%" src\main.py
if errorlevel 1 (
  echo.
  echo Creator stopped unexpectedly. Details in build\creator.log
  pause
)
