@echo off
chcp 65001 >nul
REM Запуск на Windows. Дважды кликните по файлу.
REM Список компаний положите рядом как company_list.xlsx
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
  echo.
  echo Python не найден. Установите его с python.org
  echo ВАЖНО: при установке поставьте галочку "Add Python to PATH".
  echo.
  pause
  exit /b 1
)

python -m pip install -r requirements.txt --quiet 2>nul

set IN=%1
if "%IN%"=="" set IN=company_list.xlsx
set OUT=%2
if "%OUT%"=="" set OUT=contacts_result.xlsx

if not exist "%IN%" (
  echo.
  echo Не найден файл "%IN%".
  echo Положите список рядом с этой программой и назовите company_list.xlsx
  echo 1-й столбец - название, 2-й - ИНН.
  echo.
  pause
  exit /b 1
)

REM Если рядом лежит прошлый результат - не тратим лимит API на уже найденное.
set SKIP=
if exist "Телефоны_компаний_по_ИНН.xlsx" set SKIP=--only-missing "Телефоны_компаний_по_ИНН.xlsx"
if exist "%OUT%" set SKIP=--only-missing "%OUT%"

python find_contacts.py --in "%IN%" --out "%OUT%" --delay 2 --verbose %SKIP%
echo.
pause
