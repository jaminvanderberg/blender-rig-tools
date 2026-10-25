@echo off
setlocal

set "ROOT=%~dp0"
set "SRC=%ROOT%rigtools"
set "OUT=%ROOT%rigtools.zip"

if not exist "%SRC%\__init__.py" (
    echo ERROR: rigtools\__init__.py not found.
    exit /b 1
)

if exist "%OUT%" del /f "%OUT%"

tar -a -cf "%OUT%" --exclude="*/__pycache__" --exclude="*/__pycache__/*" --exclude="*.pyc" -C "%ROOT%." rigtools

if errorlevel 1 (
    echo ERROR: Failed to create zip.
    exit /b 1
)

set "UI_SRC=%SRC%\rig_ui\rig_ui.py"
set "UI_OUT=%ROOT%rigtools_ui.py"

rem rig_ui.py must stand alone: it runs embedded in .blend files and as its own add-on
findstr /I /C:"from rigtools" /C:"import rigtools" "%UI_SRC%" >nul
if not errorlevel 1 (
    echo ERROR: rig_ui.py imports rigtools. It must not depend on the RigTools add-on.
    exit /b 1
)

copy /y "%UI_SRC%" "%UI_OUT%" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy %UI_OUT%.
    exit /b 1
)
echo Created: %UI_OUT%

echo Created: %OUT%
exit /b 0
