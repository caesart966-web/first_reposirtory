@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Документы для вступления в СРО

echo ============================================================
echo   Документы для вступления в СРО
echo ============================================================
echo.

rem ---------- 1. Ищем Python ----------
set "PYEXE="
py -3 --version >nul 2>&1 && set "PYEXE=py -3"
if not defined PYEXE (
    python --version >nul 2>&1 && set "PYEXE=python"
)
if not defined PYEXE (
    echo На компьютере не найден Python.
    echo.
    echo Что делать:
    echo   1. Откройте сайт https://www.python.org/downloads/
    echo   2. Скачайте и установите Python версии 3.10 или новее.
    echo   3. ВАЖНО: при установке поставьте галочку "Add Python to PATH".
    echo   4. Запустите этот файл снова.
    echo.
    pause
    exit /b 1
)

rem ---------- 2. Готовим окружение (только при первом запуске) ----------
if not exist ".venv\Scripts\python.exe" (
    echo Первый запуск: готовлю рабочее окружение. Это займёт 1-2 минуты...
    echo.
    %PYEXE% -m venv .venv
    if errorlevel 1 (
        echo.
        echo Не удалось создать рабочее окружение.
        echo Проверьте, что на диске есть свободное место и папка не защищена от записи.
        echo.
        pause
        exit /b 1
    )
    ".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
    echo Устанавливаю необходимые библиотеки...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo.
        echo Не удалось установить необходимые библиотеки.
        echo Чаще всего причина - нет доступа в интернет или его блокирует антивирус.
        echo.
        pause
        exit /b 1
    )
    echo Устанавливаю дополнительные возможности ^(PDF, перетаскивание файлов^)...
    ".venv\Scripts\python.exe" -m pip install -r requirements-optional.txt --quiet
    if errorlevel 1 (
        echo   Дополнительные возможности установить не удалось - это не страшно,
        echo   программа будет работать без них.
    )
    echo.
    echo Окружение готово.
    echo.
)

rem ---------- 3. Проверяем шаблоны ----------
if not exist "templates\01_Заявление_о_вступлении.docx" (
    echo Не найден шаблон заявления в папке templates.
    echo Восстановите файлы шаблонов и запустите программу снова.
    echo.
    pause
    exit /b 1
)

rem ---------- 4. Запускаем ----------
echo Запускаю программу...
".venv\Scripts\python.exe" -m src.gui
if errorlevel 1 (
    echo.
    echo ============================================================
    echo   Программа завершилась с ошибкой.
    echo ============================================================
    echo.
    echo Что можно сделать:
    echo   1. Откройте файл logs\app.log - в конце будет описание ошибки.
    echo   2. Проверьте, что документы Word не открыты в другой программе.
    echo   3. Если ошибка повторяется, удалите папку .venv и запустите START.bat снова.
    echo.
    pause
    exit /b 1
)

endlocal
