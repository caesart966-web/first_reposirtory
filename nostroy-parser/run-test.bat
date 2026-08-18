@echo off
rem Пробный запуск: обрабатывает только 3 компании, чтобы проверить,
rem что ключ API работает и контакты приходят, не потратив суточный лимит.
set "EXTRA_ARGS=--max-companies 3 --with-diagnostics"
call "%~dp0run.bat" %*
