# Python без установки — для компьютеров, где Windows запрещает ставить программы.
#
# Признак такого компьютера: установщик Python отвечает кодом 1625 («установка
# запрещена политикой системы») и ничего не ставит. Встраиваемая сборка с python.org —
# это zip-архив: его не устанавливают, а распаковывают, поэтому запрет его не касается.
# Скрипт кладёт Python в папку python\ рядом со скриптами, включает в нём установку
# пакетов и ставит requests и openpyxl.
#
# Запуск из папки со скриптами (один раз):
#     powershell -ExecutionPolicy Bypass -File python_portable.ps1
# Дальше скрипты запускаются так, без .venv и без activate:
#     python\python.exe checko_контакты.py --file москва_для_checko.xlsx
#
# Свои скрипты встраиваемый Python находит и без настройки путей: им нужны только
# стандартная библиотека и установленные сюда пакеты.

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ProgressPreference = 'SilentlyContinue'
try {
    [Net.ServicePointManager]::SecurityProtocol =
        [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
} catch { }

$version = '3.12.10'
$dir = Join-Path (Get-Location).Path 'python'
$exe = Join-Path $dir 'python.exe'

function Stop-WithError([string]$message) {
    Write-Host ""
    Write-Host $message -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $exe)) {
    $zip = Join-Path $env:TEMP "python-$version-embed-amd64.zip"
    Write-Host "Скачиваю Python $version (архив около 11 МБ)..."
    try {
        Invoke-WebRequest "https://www.python.org/ftp/python/$version/python-$version-embed-amd64.zip" `
                          -OutFile $zip -UseBasicParsing -ErrorAction Stop
        Expand-Archive -Path $zip -DestinationPath $dir -Force -ErrorAction Stop
    } catch {
        Stop-WithError "Не скачался или не распаковался архив Python: $($_.Exception.Message)"
    }
}
if (-not (Test-Path $exe)) { Stop-WithError "После распаковки нет $exe" }

# Встраиваемая сборка по умолчанию не видит установленные пакеты: в файле
# python312._pth строка «import site» закомментирована — раскомментируем
$pth = Get-ChildItem $dir -Filter 'python*._pth' | Select-Object -First 1
if ($pth) {
    $lines = Get-Content $pth.FullName
    $lines = $lines | ForEach-Object { $_ -replace '^\s*#\s*import site', 'import site' }
    Set-Content -Path $pth.FullName -Value $lines -Encoding ASCII
}

& $exe -m pip --version *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Ставлю pip..."
    $getpip = Join-Path $env:TEMP 'get-pip.py'
    try {
        Invoke-WebRequest 'https://bootstrap.pypa.io/get-pip.py' -OutFile $getpip -UseBasicParsing -ErrorAction Stop
    } catch {
        Stop-WithError "Не скачался get-pip.py: $($_.Exception.Message)"
    }
    & $exe $getpip --no-warn-script-location
    if ($LASTEXITCODE -ne 0) { Stop-WithError "pip не поставился (код $LASTEXITCODE)" }
}

Write-Host "Ставлю requests и openpyxl..."
& $exe -m pip install --no-warn-script-location --disable-pip-version-check requests openpyxl
if ($LASTEXITCODE -ne 0) { Stop-WithError "Пакеты не поставились (код $LASTEXITCODE)" }

& $exe -c "import requests, openpyxl, sys; print('Готово: Python', sys.version.split()[0], '| requests', requests.__version__, '| openpyxl', openpyxl.__version__)"
if ($LASTEXITCODE -ne 0) { Stop-WithError "Python не видит поставленные пакеты" }
Write-Host ""
Write-Host "Скрипты теперь запускаются так:" -ForegroundColor Green
Write-Host "    python\python.exe checko_контакты.py --file москва_для_checko.xlsx" -ForegroundColor Green
