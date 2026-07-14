# MCP-инструменты и функции

Агенты работают с данными только через инструменты. Ниже — высокоуровневые
MCP-функции (доменные) и низкоуровневые тул-функции (инфраструктурные).
Сигнатуры даны в псевдо-TypeScript; на практике — MCP-сервер `construction-mcp`.

## Высокоуровневые MCP-функции (доменные)

### Чтение

```ts
// Список и метаданные загруженных документов проекта.
get_project_documents(input: {
  project_id: string,
  document_type?: "contract" | "supplementary_agreement" | "estimate" | "boq" |
                  "schedule" | "design_doc" | "working_doc" | "floor_plan" |
                  "tech_card" | "quality_spec"
}): { documents: Array<{ document_id, document_type, title, version, uploaded_at, uri }> }

// Семантический + полнотекстовый поиск по договору и доп. соглашениям.
search_contract(input: {
  project_id: string, query: string, top_k?: number
}): { hits: Array<{ obligation_id?, document_id, locator, page, quote, score }> }

// Позиции сметы/ВОР, опц. фильтр по помещению/подрядчику.
get_estimate_items(input: {
  project_id: string, room_id?: string, contractor?: string
}): { items: EstimateItem[] }

// Строки графика, опц. окно дат и фильтр по помещению.
get_schedule_tasks(input: {
  project_id: string, room_id?: string, active_on?: string /* ISO date */
}): { tasks: ScheduleTask[] }

// План этажа: изображение + разметка помещений (полигоны/коды).
get_floor_plan(input: {
  floor_id: string
}): { image_uri, rooms: Array<{ room_id, code, name, plan_polygon }> }

// Сегменты видео обхода, опц. фильтр по помещению.
get_video_segments(input: {
  inspection_id: string, room_id?: string
}): { segments: VideoSegment[] }

// Ключевые кадры по сегменту/помещению/наблюдению.
get_evidence_frames(input: {
  segment_id?: string, room_id?: string, observation_id?: string, ids?: string[]
}): { frames: EvidenceFrame[] }
```

### Запись

```ts
// Сохранить наблюдение прогресса (Visual Progress Agent).
save_progress_observation(input: {
  observation: ProgressObservation
}): { observation_id: string, validated: boolean }

// Создать проблему (Schedule/Quality/Chief).
create_issue(input: {
  issue: Issue
}): { issue_id: string, validated: boolean }

// Обновить проблему (в т.ч. по результату проверки человеком).
update_issue(input: {
  issue_id: string, patch: Partial<Issue>, actor: "system" | "human", reason?: string
}): { issue_id: string, review_status: string }

// Сформировать недельный отчёт (Chief Construction Agent).
generate_weekly_report(input: {
  project_id: string, period_from: string, period_to: string, inspection_ids: string[]
}): { report_id: string, report: WeeklyReport, markdown_uri: string }

// Отправить вывод на подтверждение специалисту (human-in-the-loop).
request_human_review(input: {
  entity_type: "Issue" | "ProgressObservation" | "Defect" | "Risk" | "WeeklyReport",
  entity_id: string,
  reason: string,
  severity: "critical" | "high" | "medium" | "low" | "info",
  suggested_options?: string[]   // например: ["подтвердить", "отклонить", "исправить"]
}): { review_request_id: string, status: "queued" }
```

## Низкоуровневые тул-функции (инфраструктурные)

Обёртки над готовыми сервисами; вызываются пайплайном обработки и агентами.

```ts
// Чтение документов.
read_pdf(uri, { ocr?: boolean, pages?: string }): { text, blocks, tables, page_images }
read_docx(uri): { text, paragraphs, tables }
read_xlsx(uri, { sheet? }): { sheets: Array<{ name, rows: string[][] }> }

// Видео и медиа.
extract_frames(video_uri, { fps?: number, scene_change?: boolean, timestamps_ms?: number[] })
  : { frames: Array<{ timestamp_ms, image_uri, quality_flags }> }
transcribe_audio(video_uri | audio_uri, { language?: "ru" })
  : { segments: Array<{ start_ms, end_ms, text }> }        // ASR
run_ocr(image_uri): { text, boxes }                        // таблички/маркировка/сметы-сканы
analyze_frames(frame_uris: string[], prompt: string, schema: object)
  : object                                                 // мультимодальная LLM, строгий JSON

// Поиск.
search_documents(project_id, query, { top_k? }): { hits }  // векторный + BM25 по документам
search_video_archive(project_id, query, { top_k? }): { hits: Array<{ frame_id, room_id, score }> }

// Версии и график.
diff_documents(document_id_a, document_id_b): { changes: Array<{ locator, before, after, kind }> }
read_schedule(document_id): { tasks: ScheduleTask[] }      // парсер MPP-экспорта/XLSX/PDF

// Проектная БД (единый доступ к сущностям).
db_get(entity_type, id) / db_query(entity_type, filter) / db_upsert(entity_type, obj)

// Внешние действия.
create_pm_task(input: { title, description, assignee, due_date, priority, issue_id })
  : { pm_task_id, url }                                    // система управления проектами
update_pm_task(pm_task_id, patch)
send_notification(input: { channel: "email"|"telegram"|"webhook", to, subject, body, links })
  : { delivered: boolean }
```

## Соответствие требуемым инструментам

| Требование пользователя | Функция |
|---|---|
| загрузка и чтение PDF, DOCX, XLSX | `read_pdf`, `read_docx`, `read_xlsx` |
| извлечение кадров из видео | `extract_frames` |
| распознавание речи | `transcribe_audio` (ASR) |
| поиск по документам | `search_documents`, `search_contract` |
| поиск по видеоархиву | `search_video_archive` |
| база данных проекта | `db_*`, `get_*` |
| сравнение версий документов | `diff_documents` |
| чтение календарного графика | `read_schedule`, `get_schedule_tasks` |
| формирование отчёта | `generate_weekly_report` |
| создание задач в PM-системе | `create_pm_task`, `update_pm_task` |
| отправка уведомлений | `send_notification` |

## Права и безопасность

- Записывающие функции (`save_*`, `create_*`, `update_*`, `create_pm_task`,
  `send_notification`) требуют, чтобы у сущности была валидация по схеме и — для
  критических — пройденный `request_human_review`.
- `generate_weekly_report` не может пометить работы принятыми: в отчёте только
  наблюдения и рекомендации.
- Все функции логируют актора (агент/человек) и время для аудита.
