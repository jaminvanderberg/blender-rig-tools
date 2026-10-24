@echo off
setlocal

set "ROOT=%~dp0"
set "VENV=%ROOT%.venv"

if not exist "%VENV%\Scripts\python.exe" (
    python -m venv "%VENV%"
    if errorlevel 1 (
        echo ERROR: Failed to create .venv. Is Python installed and on PATH?
        exit /b 1
    )
)

"%VENV%\Scripts\pip" install --upgrade -r "%ROOT%requirements-dev.txt"

if errorlevel 1 (
    echo ERROR: Failed to install requirements.
    exit /b 1
)

echo Dev environment ready. Reload VS Code.
exit /b 0
