# Модель данных

Единый словарь для всех агентов и БД. Формальные схемы — `schemas/entities.schema.json`.
Идентификаторы — строки с префиксом типа (`proj_`, `bld_`, `flr_`, `zone_`, `room_`,
`obl_`, `est_`, `task_`, `insp_`, `seg_`, `frame_`, `obs_`, `def_`, `risk_`, `act_`,
`issue_`).

## Сущности

| Сущность | Назначение | Ключевые поля |
|---|---|---|
| **Project** | Проект/стройка | customer, general_contractor, planned_start/finish |
| **Building** | Объект/корпус | project_id, name |
| **Floor** | Этаж | building_id, level, floor_plan_document_id |
| **Zone** | Крупная зона на этаже (секция/ядро) | floor_id, name |
| **Room** | Помещение — базовая единица привязки | floor_id, code, area_m2, plan_polygon |
| **ContractObligation** | Обязательство/условие договора | category, summary, due_date, penalty, acceptance_requirements, source |
| **EstimateItem** | Позиция сметы/ВОР | work_name, unit, quantity, contractor, room_ids, source |
| **ScheduleTask** | Строка графика | planned_start/finish, predecessor_ids, is_hidden_work, room_ids, source |
| **Inspection** | Обход = загрузка видео за дату | date, camera_type, previous_inspection_id |
| **VideoSegment** | Смысловой эпизод, привязан к помещению | inspection_id, start_ms/end_ms, room_id, room_assignment_method, transcript |
| **EvidenceFrame** | Ключевой кадр-доказательство | segment_id, timestamp_ms, image_uri, detected_labels, ocr_text |
| **ProgressObservation** | Факт по работе в помещении на обходе | status, estimated_completion_percent, confidence, evidence_frame_ids |
| **Defect** | Дефект/подозрение | defect_status, severity, required_checks, evidence_frame_ids |
| **Risk** | Вероятное будущее событие | category, likelihood, impact |
| **CorrectiveAction** | Рекомендуемое мероприятие | action, responsible, due_date, priority |
| **Issue** | Единый объект проблемы (см. `issue.schema.json`) | всё выше + план/факт/отклонение/просрочка/HITL |

## Связи (ER, текстом)

```
Project 1─┬─N Building 1──N Floor 1──N Zone 1──N Room
          ├─N ContractObligation ─┐
          ├─N EstimateItem ───────┼─(N:N через room_ids / linked_* / cross_links)
          ├─N ScheduleTask ───────┘
          └─N Inspection 1──N VideoSegment 1──N EvidenceFrame
                                        │
ProgressObservation }── room_id, schedule_task_id, estimate_item_id, evidence_frame_ids
Defect              }── room_id, requirement_source, evidence_frame_ids
Risk                }── affected_room_ids, affected_schedule_task_ids
Issue               }── агрегирует observation/defect/risk + все ссылки
CorrectiveAction    }── issue_id, pm_task_id
```

Ключевые «мостики» модели (то, что делает выводы трассируемыми):

- **Room** — узел привязки в MVP без BIM. К нему тянутся `EstimateItem.room_ids`,
  `ScheduleTask.room_ids`, `VideoSegment.room_id`, `ProgressObservation.room_id`,
  `Defect.room_id`. Именно через Room факт с видео встречается с планом.
- **cross_links** (выход Document Extraction) — связи обязательство ↔ смета ↔
  график, чтобы в `Issue` можно было проставить `contract_obligation_id`,
  `estimate_item_id`, `schedule_task_id` одновременно.
- **EvidenceFrame** — единственный допустимый источник фактических утверждений о
  прогрессе/дефектах. Нет кадра — нет факта.
- **SourceRef** — ссылка на место в документе (document_id + locator + quote),
  обеспечивает «до строки договора».

## Инварианты (проверять при записи)

1. `ProgressObservation.evidence_frame_ids` не пуст, если `status ≠ not_started`.
2. `estimated_completion_percent = 0` ⇔ `status = not_started`;
   `= 100` допускается только при `status = visually_complete`.
3. `Issue.requires_human_review = true`, если `severity = critical`, либо работа
   `is_hidden_work`, либо `confidence < 0.5`, либо есть юр./фин. последствия.
4. `Defect.defect_status = confirmed_visual` запрещён для скрытых работ и для
   требований из `non_verifiable_by_video` — там только `needs_instrumental_check`.
5. Любая ссылка (`*_id`) либо указывает на существующую сущность, либо `null`.
   «Полу-выдуманные» ссылки запрещены.
6. `deviation_percent = actual_percent − planned_percent` (знак: минус = отставание).

## Жизненный цикл вывода (review_status)

`pending_review → {confirmed | corrected | rejected | escalated}`; либо
`auto_accepted` для некритичных выводов с `confidence ≥ порога` (см.
`human-in-the-loop.md`). Правки (`corrected`) сохраняют и исходное, и
исправленное значение — для последующей оценки качества системы.
