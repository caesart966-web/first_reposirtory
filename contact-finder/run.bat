@echo off
rem Запуск под Windows: создаёт venv, ставит зависимости, запускает сбор
rem и в конце открывает папку с результатом.
chcp 65001 >nul
setlocal

set "HERE=%~dp0"
cd /d "%HERE%"

if not exist ".venv\Scripts\python.exe" (
    echo Создаю виртуальное окружение...
    python -m venv .venv || goto :error
)
call ".venv\Scripts\activate.bat"

echo Устанавливаю зависимости...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt || goto :error

if not exist ".env" (
    if exist ".env.example" copy /y ".env.example" ".env" >nul
    echo Внимание: заполните ключи API в файле .env
)

set "INPUT=%~1"
if "%INPUT%"=="" set "INPUT=companies.xlsx"
set "DEST=%HERE%out"
if not exist "%DEST%" mkdir "%DEST%"

echo Запускаю сбор: вход %INPUT%
python finder.py --input "%INPUT%" --output "%DEST%\result.xlsx" --errors-file "%DEST%\errors.xlsx" --sources all --depth full
if errorlevel 1 goto :error

echo.
echo Готово. Открываю папку с результатом...
explorer "%DEST%"
goto :eof

:error
echo.
echo Произошла ошибка. Подробности в logs\finder.log
pause
exit /b 1
