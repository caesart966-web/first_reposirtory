# Обновление кода из GitHub без скачивания всего репозитория.
#
# Качает только папку tools/moscow-companies-db: отдельные скрипты и пакет
# mosstroybase. База (mosstroybase.sqlite3), выгрузки и .venv не трогаются.
#
# Запуск из папки C:\mosstroybase:
#     powershell -ExecutionPolicy Bypass -File обновить.ps1
#
# Список файлов берётся из GitHub API, поэтому новые скрипты подхватятся
# сами — правки в этот файл при их появлении не нужны.

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$owner  = 'caesart966-web'
$repo   = 'first_reposirtory'
$branch = 'claude/moscow-construction-companies-db-khnge4'
$root   = 'tools/moscow-companies-db'

# Подпапки пакета: путь в репозитории -> путь на диске
$folders = @(
    @{ Remote = $root;                       Local = '.' },
    @{ Remote = "$root/mosstroybase";        Local = 'mosstroybase' },
    @{ Remote = "$root/mosstroybase/sources"; Local = 'mosstroybase\sources' }
)

$updated = 0
$skipped = 0

foreach ($folder in $folders) {
    $api = "https://api.github.com/repos/$owner/$repo/contents/$($folder.Remote)?ref=$branch"
    try {
        $items = Invoke-RestMethod -Uri $api -Headers @{ 'User-Agent' = 'mosstroybase-updater' }
    } catch {
        Write-Host "не удалось прочитать $($folder.Remote): $_" -ForegroundColor Red
        continue
    }

    if (-not (Test-Path $folder.Local)) {
        New-Item -ItemType Directory -Path $folder.Local -Force | Out-Null
    }

    foreach ($item in $items) {
        # Берём только код и требования; README и папки пропускаем
        if ($item.type -ne 'file') { continue }
        if ($item.name -notmatch '\.(py|txt|ps1)$') { continue }

        $target = Join-Path $folder.Local $item.name

        # Сравниваем с тем, что уже лежит, чтобы не трогать неизменившееся
        $newBytes = (Invoke-WebRequest -Uri $item.download_url -UseBasicParsing).Content
        if ($newBytes -is [string]) {
            $newBytes = [System.Text.Encoding]::UTF8.GetBytes($newBytes)
        }
        if (Test-Path $target) {
            $oldBytes = [System.IO.File]::ReadAllBytes($target)
            if (@(Compare-Object $oldBytes $newBytes -SyncWindow 0).Count -eq 0) {
                $skipped++
                continue
            }
        }
        [System.IO.File]::WriteAllBytes($target, $newBytes)
        Write-Host "обновлён: $target" -ForegroundColor Green
        $updated++
    }
}

Write-Host ""
if ($updated -eq 0) {
    Write-Host "всё уже актуально (проверено файлов: $skipped)"
} else {
    Write-Host "обновлено файлов: $updated, без изменений: $skipped"
}
