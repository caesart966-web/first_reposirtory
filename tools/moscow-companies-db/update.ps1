# Обновление кода mosstroybase из GitHub — без скачивания всего репозитория.
#
# Качает только папку tools/moscow-companies-db: скрипты в корне и пакет
# mosstroybase. База (mosstroybase.sqlite3), выгрузки, .venv и всё остальное,
# что лежит рядом, не трогаются.
#
# Запуск из папки C:\mosstroybase:
#     powershell -ExecutionPolicy Bypass -File update.ps1
#
# Если самого update.ps1 ещё нет, он качается одной командой (см. README).
#
# Список файлов берётся из GitHub API, поэтому новые скрипты подхватываются
# сами — править этот файл при их появлении не нужно.

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
# Без этого Invoke-WebRequest в PowerShell 5.1 рисует прогресс-бар и тормозит в разы
$ProgressPreference = 'SilentlyContinue'
# Старые Windows по умолчанию не умеют TLS 1.2, а GitHub других не принимает
try {
    [Net.ServicePointManager]::SecurityProtocol =
        [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
} catch { }

$owner  = 'caesart966-web'
$repo   = 'first_reposirtory'
$branch = 'claude/moscow-construction-companies-db-khnge4'
$root   = 'tools/moscow-companies-db'
$agent  = @{ 'User-Agent' = 'mosstroybase-updater' }

# Что откуда качаем: путь в репозитории -> папка на диске
$folders = @(
    @{ Remote = $root;                        Local = '.' },
    @{ Remote = "$root/mosstroybase";         Local = 'mosstroybase' },
    @{ Remote = "$root/mosstroybase/sources"; Local = 'mosstroybase\sources' }
)

# GitHub отдаёт для каждого файла его git-хеш. Считаем такой же локально —
# тогда неизменившиеся файлы даже не скачиваются.
function Get-GitBlobSha {
    param([string]$Path)
    $bytes  = [System.IO.File]::ReadAllBytes($Path)
    $header = [System.Text.Encoding]::ASCII.GetBytes("blob $($bytes.Length)`0")
    $all    = New-Object byte[] ($header.Length + $bytes.Length)
    [Array]::Copy($header, 0, $all, 0, $header.Length)
    [Array]::Copy($bytes,  0, $all, $header.Length, $bytes.Length)
    $sha1 = [System.Security.Cryptography.SHA1]::Create()
    -join ($sha1.ComputeHash($all) | ForEach-Object { $_.ToString('x2') })
}

Write-Host "PowerShell $($PSVersionTable.PSVersion), папка $((Get-Location).Path)"
Write-Host "ветка $branch"
Write-Host ""

$updated = @()
$skipped = 0
$failed  = @()

foreach ($folder in $folders) {
    $api = "https://api.github.com/repos/$owner/$repo/contents/$($folder.Remote)?ref=$branch"
    try {
        $items = @(Invoke-RestMethod -Uri $api -Headers $agent -ErrorAction Stop)
    } catch {
        $failed += "$($folder.Remote) — $($_.Exception.Message)"
        Write-Host "не удалось прочитать $($folder.Remote): $($_.Exception.Message)" -ForegroundColor Red
        continue
    }

    if (-not (Test-Path $folder.Local)) {
        New-Item -ItemType Directory -Path $folder.Local -Force | Out-Null
    }

    # Берём только код и требования; README и вложенные папки пропускаем
    $files = @($items | Where-Object { $_.type -eq 'file' -and $_.name -match '\.(py|txt|ps1)$' })
    Write-Host "$($folder.Remote): файлов в репозитории — $($files.Count)"

    foreach ($item in $files) {
        $target = Join-Path $folder.Local $item.name

        if ((Test-Path $target) -and (Get-GitBlobSha $target) -eq $item.sha) {
            $skipped++
            continue
        }

        $tmp = [System.IO.Path]::GetTempFileName()
        try {
            Invoke-WebRequest -Uri $item.download_url -OutFile $tmp -Headers $agent `
                              -UseBasicParsing -ErrorAction Stop
            Move-Item -LiteralPath $tmp -Destination $target -Force -ErrorAction Stop
            Write-Host "  обновлён: $target" -ForegroundColor Green
            $updated += $target
        } catch {
            $failed += "$($item.name) — $($_.Exception.Message)"
            Write-Host "  не скачался $($item.name): $($_.Exception.Message)" -ForegroundColor Red
            Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Host ""
if ($updated.Count -eq 0 -and $failed.Count -eq 0) {
    Write-Host "всё уже актуально (проверено файлов: $skipped)"
} else {
    Write-Host "обновлено: $($updated.Count), без изменений: $skipped, с ошибкой: $($failed.Count)"
}
if ($failed.Count -gt 0) {
    Write-Host ""
    Write-Host "ошибки:" -ForegroundColor Red
    $failed | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    exit 1
}
