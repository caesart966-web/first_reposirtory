@echo off
rem Ежедневный запуск через Планировщик задач Windows (08:00).
rem Действие: "Запустить программу", программа: полный путь к этому run.bat,
rem "Рабочая папка": папка проекта.
chcp 65001 >nul
cd /d "%~dp0"
set DEST=%~dp0output
python run.py --full
explorer "%DEST%"
