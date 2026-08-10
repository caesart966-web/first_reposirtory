@echo off
REM Запуск на Windows. Дважды кликните по файлу или запустите из cmd.
REM Список компаний положите рядом как company_list.xlsx
cd /d "%~dp0"

python -m pip install -r requirements.txt --quiet 2>nul

set IN=%1
if "%IN%"=="" set IN=company_list.xlsx
set OUT=%2
if "%OUT%"=="" set OUT=contacts_result.xlsx

python find_contacts.py --in "%IN%" --out "%OUT%" --delay 2 --verbose
pause
