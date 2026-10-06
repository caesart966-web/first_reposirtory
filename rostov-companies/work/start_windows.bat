@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY goto nopython
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" || goto nopython
%PY% -c "import openpyxl" 2>nul || %PY% -m pip install --quiet --disable-pip-version-check --user openpyxl
%PY% checko_status.py %*
echo.
pause
exit /b

:nopython
echo Не найден Python 3.8 или новее.
echo Установите его с https://www.python.org/downloads/ - при установке отметьте галочку "Add Python to PATH",
echo затем снова запустите этот файл двойным щелчком.
pause
