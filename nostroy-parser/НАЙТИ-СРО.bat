@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo  В каких СРО состоят компании
echo ============================================================
echo.
echo Источник: открытые реестры НОСТРОЙ и НОПРИЗ.
echo Ключ и лимит checko.ru здесь не нужны — реестры бесплатны.
echo.

set "PY=.venv\Scripts\python.exe"
if exist "%PY%" goto have_python
where python >nul 2>nul
if errorlevel 1 goto no_python
set "PY=python"
"%PY%" -m pip install -r requirements.txt --quiet
:have_python

set "INPUT=%~1"
if not "%INPUT%"=="" goto have_input
echo Перетащите Excel со списком компаний в это окно
set /p "INPUT=и нажмите Enter: "
set "INPUT=%INPUT:"=%"
:have_input
if not exist "%INPUT%" goto not_found

"%PY%" find_sro.py "%INPUT%"
if errorlevel 1 goto failed

echo.
echo ============================================================
echo  Готово. Файл с пометкой _СРО лежит рядом с исходным.
echo ============================================================
pause
exit /b 0

:no_python
echo Python не найден. Запустите сначала run.bat — он всё установит.
pause
exit /b 1

:not_found
echo Файл не найден: %INPUT%
pause
exit /b 1

:failed
echo.
echo Не получилось. Скопируйте текст выше и пришлите его.
pause
exit /b 1
