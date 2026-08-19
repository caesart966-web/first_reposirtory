@echo off
setlocal
cd /d "%~dp0"
title Diagnostika SRO

rem ---------------------------------------------------------------
rem  Pure ASCII + CRLF only. All Russian text is printed by
rem  scripts\selftest.py (see START.bat for why).
rem ---------------------------------------------------------------

set "PYEXE="
if exist ".venv\Scripts\python.exe" set "PYEXE=.venv\Scripts\python.exe"
if not defined PYEXE (
    py -3 --version >nul 2>&1 && set "PYEXE=py -3"
)
if not defined PYEXE (
    python --version >nul 2>&1 && set "PYEXE=python"
)
if not defined PYEXE goto no_python

%PYEXE% "scripts\selftest.py"
echo.
echo  Report saved to  logs\DIAGNOSTIKA.txt
echo.
pause
exit /b 0

:no_python
echo.
echo  Python not found. See SETUP_PYTHON.txt
echo.
pause
exit /b 1
