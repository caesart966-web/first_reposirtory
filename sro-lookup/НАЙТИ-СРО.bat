@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo  В каких СРО состоят компании
echo ============================================================
echo.
echo Источник: открытые реестры НОСТРОЙ и НОПРИЗ.
echo Ключи и лимиты не нужны — реестры бесплатны.
echo.

where python >nul 2>nul
if errorlevel 1 goto no_python

if exist ".venv\Scripts\python.exe" goto env_ready
echo Первый запуск: создаю окружение и ставлю зависимости.
echo Это займёт пару минут. Следующие запуски будут быстрыми.
echo.
python -m venv .venv
if errorlevel 1 goto venv_failed
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
if errorlevel 1 goto pip_failed
echo Готово.
echo.
:env_ready

set "INPUT=%~1"
if not "%INPUT%"=="" goto have_input
echo Перетащите Excel со списком компаний в это окно
set /p "INPUT=и нажмите Enter: "
set "INPUT=%INPUT:"=%"
:have_input
if "%INPUT%"=="" goto no_input
if not exist "%INPUT%" goto not_found

echo.
".venv\Scripts\python.exe" find_sro.py "%INPUT%"
if errorlevel 1 goto failed

echo.
echo ============================================================
echo  Готово. Файл с пометкой _СРО лежит рядом с исходным.
echo ============================================================
pause
exit /b 0

:no_python
echo Python не найден.
echo Установите его с python.org, отметив галочку "Add Python to PATH".
pause
exit /b 1

:venv_failed
echo Не удалось создать окружение .venv
pause
exit /b 1

:pip_failed
echo Не удалось установить зависимости. Проверьте интернет.
pause
exit /b 1

:no_input
echo Файл не указан.
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
