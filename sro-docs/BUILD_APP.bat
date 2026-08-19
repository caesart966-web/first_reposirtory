@echo off
setlocal
cd /d "%~dp0"
title Build SRO app

rem ---------------------------------------------------------------
rem  Builds the app into one file and prepares a folder to hand to
rem  colleagues. Pure ASCII + CRLF (see START.bat for why). The
rem  Russian messages and the final folder path are printed by
rem  scripts\build_app.py, not from here.
rem ---------------------------------------------------------------

if not exist ".venv\Scripts\python.exe" goto no_venv

echo Installing PyInstaller (one time, needs internet)...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --no-warn-script-location pyinstaller
if errorlevel 1 goto fail

".venv\Scripts\python.exe" "scripts\build_app.py"
if errorlevel 1 goto fail

echo.
echo  Done. The ready-to-share folder path is printed above by the builder.
echo.
pause
exit /b 0

:no_venv
echo.
echo  Run START.bat once first - it creates the .venv environment.
echo.
pause
exit /b 1

:fail
echo.
echo  Build failed - see the message above.
echo.
pause
exit /b 1
