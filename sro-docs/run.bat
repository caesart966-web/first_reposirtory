@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0make_docs.py" %*
) else (
  python "%~dp0make_docs.py" %*
)
echo.
pause
