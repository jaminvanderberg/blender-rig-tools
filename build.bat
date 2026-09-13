@echo off
setlocal

set "ROOT=%~dp0"
set "SRC=%ROOT%rigtools"
set "OUT=%ROOT%rigtools.zip"

if not exist "%SRC%\__init__.py" (
    echo ERROR: color_id\__init__.py not found.
    exit /b 1
)

if exist "%OUT%" del /f "%OUT%"

powershell -NoProfile -Command ^
  "Compress-Archive -Path '%SRC%' -DestinationPath '%OUT%' -Force"

if errorlevel 1 (
    echo ERROR: Failed to create zip.
    exit /b 1
)

echo Created: %OUT%
exit /b 0
