@echo off
chcp 65001
cd /d "%~dp0"
title Probiv kontaktov cherez Checko
echo.
echo === Rabochaya papka: %CD%
echo.

set PY=python
python --version
if not errorlevel 1 goto HAVEPY

set PY=py
py --version
if not errorlevel 1 goto HAVEPY

echo.
echo =====================================================
echo   Python ne nayden na etom kompyutere.
echo   Skachayte: https://www.python.org/downloads/
echo   Pri ustanovke postavte galochku:
echo   "Add python.exe to PATH"
echo =====================================================
echo.
pause
exit /b 1

:HAVEPY
echo.
%PY% -m pip install openpyxl
echo.
%PY% probiv.py 
echo.
echo === Gotovo. Okno mozhno zakryt.
pause
