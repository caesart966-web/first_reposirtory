@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo  Починка готового отчёта: один адрес, короткие названия
echo ============================================================
echo.
echo Ничего не скачивается и не запрашивается.
echo Исходный файл не меняется — рядом появится новый,
echo с пометкой _исправлен в имени.
echo.

rem --- Python: берём окружение проекта, иначе системный --------------------
set "PY=.venv\Scripts\python.exe"
if exist "%PY%" goto have_python
where python >nul 2>nul
if errorlevel 1 goto no_python
set "PY=python"
"%PY%" -m pip install openpyxl --quiet
:have_python

rem --- Файл: перетащенный на .bat либо самый свежий из output --------------
"%PY%" fix_report.py %1
if errorlevel 1 goto failed

echo.
echo ============================================================
echo  Готово. Откройте файл с пометкой _исправлен.
echo ============================================================
pause
exit /b 0

:no_python
echo Python не найден. Запустите сначала run.bat — он всё установит.
pause
exit /b 1

:failed
echo.
echo Не получилось. Скопируйте текст выше и пришлите его.
pause
exit /b 1
