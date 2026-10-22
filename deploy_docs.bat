@echo off
setlocal

set "ROOT=%~dp0"
set "CONFIG=%ROOT%mkdocs.yml"
set "REMOTE=rig-tools"

if not exist "%CONFIG%" (
    echo ERROR: mkdocs.yml not found.
    exit /b 1
)

rem pushd maps a temporary drive letter when the repo is on a network share
pushd "%ROOT%"

rem --strict stops the deploy if there are broken links or other warnings
python -m mkdocs gh-deploy --strict --config-file "%CONFIG%" --remote-name %REMOTE%

if errorlevel 1 (
    echo ERROR: Failed to deploy docs.
    popd
    exit /b 1
)

popd
echo Deployed: https://jaminvanderberg.github.io/blender-rig-tools/
exit /b 0
