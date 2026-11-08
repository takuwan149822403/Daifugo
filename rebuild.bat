@echo off
setlocal
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONUNBUFFERED=1
pushd "%~dp0"
if errorlevel 1 exit /b 1

for %%P in (.venv313 .venv-build .venv) do if exist "%%P\Scripts\python.exe" (
    set "REBUILD_PYTHON=%%P\Scripts\python.exe"
    goto run_environment
)
py -3.13 -c "import sys" >nul 2>&1
if not errorlevel 1 goto run_launcher
python -c "import sys" >nul 2>&1
if not errorlevel 1 goto run_python
echo Install Python 3.13, then run rebuild.bat again.
set REBUILD_STATUS=1
goto finish

:run_environment
"%REBUILD_PYTHON%" -u rebuild.py
set "REBUILD_STATUS=%ERRORLEVEL%"
goto finish

:run_launcher
py -3.13 -u rebuild.py
set "REBUILD_STATUS=%ERRORLEVEL%"
goto finish

:run_python
python -u rebuild.py
set "REBUILD_STATUS=%ERRORLEVEL%"

:finish
echo.
pause
popd
exit /b %REBUILD_STATUS%
