# construction-mcp — backend ИИ-ассистента строительного контроля

Референс-реализация серверной части скилла **`/construction-control`**: MCP-сервер,
который предоставляет реальные инструменты (`get_estimate_items`, `create_issue`,
`generate_weekly_report` и др.) поверх локальной БД (SQLite), парсеров документов,
обработки видео и мультимодального анализа кадров.

Это **Level 2** проекта: скилл описывает методологию и промпты агентов, а этот
backend делает инструменты вызываемыми. Работает end-to-end локально; внешние
сервисы (мультимодальная LLM, OCR, ASR, ffmpeg) — подключаемые, при их отсутствии
конвейер деградирует до офлайн-заглушек, а не падает.

## Что реализовано

- **MCP-сервер (stdio)** — 22 инструмента: 12 доменных функций скилла + 10
  низкоуровневых (чтение PDF/DOCX/XLSX, разбор графика, кадры, ASR, OCR, анализ
  кадров, поиск).
- **Единая модель данных на SQLite** — generic document store, мигрируется на
  Postgres/JSONB. Сущности валидируются по JSON Schema скилла (единый источник истины).
- **Детерминированный расчёт отклонений** (`deviation.py`) — план/факт, просрочка,
  прогноз, последовательность.
- **Парсеры** PDF (pdfplumber), DOCX (python-docx), XLSX (openpyxl) + эвристический
  разбор графика.
- **Видео**: извлечение кадров через ffmpeg (если установлен); ASR/OCR — через
  внешние провайдеры по env-командам.
- **Мультимодальный анализ кадров** через Claude API (`anthropic`); без ключа —
  безопасная офлайн-заглушка с низкой уверенностью и `requires_human_review`.
- **Поиск** по документам/видеоархиву — лексический (RU), с точкой расширения на
  эмбеддинги/вектор.
- **Human-in-the-loop**: очередь `request_human_review`, журнал правок человека.

## Требования

- Python 3.10+
- (опц.) `ffmpeg` в PATH — для извлечения кадров из видео
- (опц.) `ANTHROPIC_API_KEY` — для реального анализа кадров (иначе офлайн-режим)

## Установка и проверка

```bash
cd backend/construction-mcp
bash setup.sh                     # создаёт .venv и ставит зависимости
make test                         # 15 тестов, должны пройти
make demo                         # сквозной прогон: факт → расчёт → Issue → отчёт
make smoke                        # проверка MCP-хендшейка по stdio
```

## Подключение к Claude Code (делает Level 2 «живым»)

Чтобы у скилла `/construction-control` в сессии появились реальные инструменты,
зарегистрируйте MCP-сервер: скопируйте образец в корень репозитория как `.mcp.json`.

```bash
cp backend/construction-mcp/mcp.json.example .mcp.json
```

`.mcp.json` запускает `backend/construction-mcp/run.sh` — самобутстрапящийся launcher:
при первом старте он сам создаёт `.venv` и ставит зависимости (весь лог — в stderr,
stdout отдан MCP-протоколу), далее сразу поднимает сервер. В новой сессии Claude
Code на этом репозитории инструменты появятся автоматически.

- **Локально:** после `cp` перезапустите сессию Claude Code.
- **Claude Code на вебе (облачные сессии):** свежий клон не содержит `.venv`.
  `run.sh` создаст его при первом запуске сервера; либо пропишите
  `bash backend/construction-mcp/setup.sh` как setup-скрипт окружения
  (docs: Claude Code on the web → Setup scripts), чтобы окружение готовилось заранее.

## Конфигурация (переменные окружения)

| Переменная | Назначение | Дефолт |
|---|---|---|
| `CONSTRUCTION_MCP_DB` | путь к файлу SQLite | `data/construction.db` |
| `CONSTRUCTION_MCP_STORAGE` | каталог видео/кадров/отчётов | `data/storage` |
| `CONSTRUCTION_SKILL_DIR` | путь к `.claude/skills/construction-control` | автопоиск |
| `ANTHROPIC_API_KEY` | ключ для анализа кадров | — (офлайн) |
| `CONSTRUCTION_MCP_VISION_MODEL` | модель для кадров | `claude-sonnet-5` |
| `CONSTRUCTION_MCP_ASR_CMD` | внешняя команда ASR (`{path} {lang}` → JSON-сегменты) | — |
| `CONSTRUCTION_MCP_OCR_CMD` | внешняя команда OCR (`{path}` → текст) | — |
| `CONSTRUCTION_MCP_OFFLINE` | принудительный офлайн | по наличию ключа |
| `CONSTRUCTION_MCP_TOLERANCE_PP` / `_OVERDUE_DAYS_HIGH` / `_LOW_CONFIDENCE` | пороги расчётов | 5 / 7 / 0.5 |

## Инструменты MCP

Доменные (12): `get_project_documents`, `search_contract`, `get_estimate_items`,
`get_schedule_tasks`, `get_floor_plan`, `get_video_segments`, `get_evidence_frames`,
`save_progress_observation`, `create_issue`, `update_issue`, `generate_weekly_report`,
`request_human_review`.
Низкоуровневые (10): `ingest_document`, `read_pdf`, `read_docx`, `read_xlsx`,
`read_schedule`, `extract_frames`, `transcribe_audio`, `run_ocr`, `analyze_frames`,
`search_documents`.

## Структура

```
construction_mcp/
  server.py      MCP-сервер (stdio), реестр инструментов
  tools.py       реализация 12 доменных + низкоуровневых функций
  db.py          SQLite-хранилище (сущности, чанки, HITL)
  schemas.py     валидация по JSON Schema скилла
  deviation.py   детерминированные расчёты отклонений
  parsers.py     PDF/DOCX/XLSX + разбор графика
  media.py       кадры (ffmpeg), ASR, OCR
  vision.py      мультимодальный анализ кадров (Claude / офлайн-заглушка)
  search.py      лексический/векторный поиск
  config.py      настройки из окружения
  ids.py         генерация id
tests/           pytest (deviation, db, parsers, tools)
examples/        demo_seed.py — сквозной прогон
scripts/         mcp_smoke.py — проверка MCP-протокола
```

## От MVP к продакшену (точки расширения)

Реализовано на самодостаточных/локальных компонентах; для прод-масштаба заменить:

| MVP сейчас | Прод |
|---|---|
| SQLite (generic store) | PostgreSQL + JSONB, миграции |
| локальный файловый storage | объектное хранилище (S3/MinIO) |
| лексический поиск | эмбеддинги + векторная БД (внедрить `search.embed`) |
| ASR/OCR по внешней команде | управляемые сервисы (Whisper/облачный ASR, Tesseract/облачный OCR) |
| ffmpeg локально | сервис извлечения кадров + разворот 360° (py360convert) |
| офлайн-заглушка кадров | Claude API (задать `ANTHROPIC_API_KEY`) |
| без авторизации | аутентификация/ACL на инструменты, аудит |

Незыблемые правила скилла соблюдаются на уровне backend'а: `create_issue`
принудительно ставит `requires_human_review` для critical/низкой уверенности и
кладёт вывод в очередь на подтверждение; отчёт всегда содержит `disclaimer` и не
может пометить работы принятыми; скрытые работы не получают `confirmed_visual`.
