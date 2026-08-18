@echo off
setlocal
cd /d "%~dp0"
title Dokumenty SRO

rem ---------------------------------------------------------------
rem  WARNING FOR DEVELOPERS / VNIMANIE RAZRABOTCHIKAM
rem  This file MUST stay pure ASCII with CRLF line endings.
rem  cmd.exe reads a batch file byte by byte and loses its position
rem  on multi-byte (Cyrillic) characters: every command after that
rem  gets cut in half and fails with
rem  "is not recognized as an internal or external command".
rem  All Russian text for the user is printed by scripts\bootstrap.py
rem  and scripts\explain_error.py instead.
rem ---------------------------------------------------------------

set "PYEXE="
py -3 --version >nul 2>&1 && set "PYEXE=py -3"
if not defined PYEXE (
    python --version >nul 2>&1 && set "PYEXE=python"
)
if not defined PYEXE goto no_python

%PYEXE% "scripts\bootstrap.py"
if errorlevel 1 goto setup_failed

".venv\Scripts\python.exe" -m src.gui
if errorlevel 1 goto run_failed

exit /b 0


:no_python
echo.
echo  Python not found. Opening instructions in Notepad...
echo.
if exist "SETUP_PYTHON.txt" start "" notepad.exe "SETUP_PYTHON.txt"
echo  Python ne naiden - smotrite fail SETUP_PYTHON.txt
echo.
pause
exit /b 1


:setup_failed
echo.
echo  Prichina napisana vyshe po-russki.
echo.
pause
exit /b 1


:run_failed
echo.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "scripts\explain_error.py"
) else (
    echo  Oshibka zapuska. Smotrite fail logs\app.log
)
echo.
pause
exit /b 1