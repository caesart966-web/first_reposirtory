@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Probiv kontaktov cherez Checko

set PY=
where python >/dev/null 2>/dev/null && set PY=python
if not defined PY (
  where py >/dev/null 2>/dev/null && set PY=py
)
if not defined PY goto NOPYTHON

%PY% -c "import openpyxl" >/dev/null 2>nul
if errorlevel 1 (
  echo Ustanavlivayu biblioteku openpyxl...
  %PY% -m pip install openpyxl
)

%PY% probiv.py --reset-day
goto END

:NOPYTHON
echo.
echo Python ne nayden. Skachayte ego: https://www.python.org/downloads/
echo Pri ustanovke obyazatelno postavte galochku "Add python.exe to PATH".
echo.

:END
echo.
pause
