@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo  Парсер реестра НОСТРОЙ + checko.ru
echo ============================================================
echo.

rem --- 1. Проверяем, что установлен Python 3.10+ -------------------------
where python >nul 2>nul
if errorlevel 1 goto no_python
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>nul
if errorlevel 1 goto old_python

rem --- 2. При первом запуске создаём окружение и ставим зависимости ------
if exist ".venv\Scripts\python.exe" goto env_ready
echo Первый запуск: создаю окружение и ставлю зависимости.
echo Это займёт пару минут. Следующие запуски будут быстрыми.
echo.
python -m venv .venv
if errorlevel 1 goto venv_failed
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
if errorlevel 1 goto pip_failed
echo Зависимости установлены.
echo.
:env_ready

rem --- 3. Определяем, что разбирать --------------------------------------
rem Файл, обработанный в прошлый раз, запоминается в last_input.txt:
rem на следующий день достаточно двойного щелчка по run.bat.
set "INPUT=%~1"
if not "%INPUT%"=="" goto have_input
if not exist "last_input.txt" goto ask_input
set /p LAST=<last_input.txt
if "%LAST%"=="" goto ask_input
if not exist "%LAST%" goto ask_input
echo Прошлый раз обрабатывался файл:
echo   %LAST%
choice /c 1_2 /n /m "Нажмите 1 — продолжить с ним, 2 — выбрать другой файл: "
if errorlevel 2 goto ask_input
set "INPUT=%LAST%"
goto have_input
:ask_input
echo Перетащите архив (.rar/.zip) или Excel-файл в это окно
set /p "INPUT=и нажмите Enter: "
set "INPUT=%INPUT:"=%"
:have_input
if "%INPUT%"=="" goto no_input
if not exist "%INPUT%" goto not_found
echo %INPUT%>last_input.txt

rem --- 4. Запускаем и по завершении открываем готовую таблицу ------------
echo.
".venv\Scripts\python.exe" main.py --input "%INPUT%" --output output --open-report %EXTRA_ARGS% %2 %3 %4 %5 %6
echo.
echo ============================================================
echo  Готовая таблица открыта в Excel.
echo  Файл лежит здесь: %~dp0output
echo ============================================================
goto done

:no_python
echo ОШИБКА: Python не найден.
echo Скачайте его с https://www.python.org/downloads/
echo При установке обязательно отметьте галочку "Add Python to PATH".
goto done

:old_python
echo ОШИБКА: нужен Python версии 3.10 или новее. Установлена:
python --version
goto done

:venv_failed
echo ОШИБКА: не удалось создать виртуальное окружение .venv
goto done

:pip_failed
echo ОШИБКА: не удалось установить зависимости.
echo Проверьте подключение к интернету и запустите файл ещё раз.
goto done

:no_input
echo ОШИБКА: файл не указан.
goto done

:not_found
echo ОШИБКА: файл или папка не найдены:
echo %INPUT%
goto done

:done
echo.
pause
