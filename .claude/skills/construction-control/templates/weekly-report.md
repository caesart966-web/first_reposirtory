# Недельный отчёт строительного контроля

> **Информационный документ.** Отчёт сформирован ИИ-ассистентом на основе анализа
> документов и видеообхода. **Не является приёмкой работ, не подтверждает скрытые
> работы и не заменяет освидетельствование и исполнительную документацию.** Выводы
> с пометкой «на подтверждение» подлежат проверке специалистом.

- **Проект:** {{project.name}} · {{project.address}}
- **Заказчик / Генподрядчик:** {{project.customer}} / {{project.general_contractor}}
- **Период:** {{period.from}} — {{period.to}}
- **Обходы:** {{period.inspection_ids}}
- **Сформирован:** {{generated_at}}

---

## 1. Резюме

{{executive_summary}}

## 2. Ключевые показатели (KPI)

| Показатель | Значение |
|---|---|
| Плановая готовность | {{kpi.overall_planned_percent}}% |
| Фактическая готовность | {{kpi.overall_actual_percent}}% |
| Отклонение | {{kpi.overall_deviation_percent}} п.п. |
| Задач в графике / отстают / просрочены | {{kpi.tasks_on_track}} / {{kpi.tasks_behind}} / {{kpi.tasks_overdue}} |
| Открытых дефектов | {{kpi.open_defects}} |
| Покрытие обходом | {{kpi.coverage_percent}}% |
| Прогноз завершения | {{kpi.forecast_project_finish}} |

## 3. Проблемы по критичности

Для каждой проблемы (отсортировано critical → info):

### [{{severity}}] {{work_name}} — {{location_label}}
- **Класс:** {{issue_kind}} · **Подрядчик:** {{contractor}}
- **Ссылки:** договор {{contract_ref}} · смета {{estimate_ref}} · график {{schedule_ref}}
- **План / Факт / Отклонение:** {{planned_percent}}% / {{actual_percent}}% / {{deviation_percent}} п.п.
- **Просрочка:** {{days_overdue}} дн. · **Прогноз:** {{forecast_finish}}
- **Уверенность:** {{confidence_level}} ({{confidence}})
- **Доказательства:** {{evidence_description}} · кадры: {{evidence_frame_ids}}
- **Причины:** {{possible_causes}}
- **Последствия:** {{consequences}} · влияет на: {{impacted_schedule_task_ids}}
- **Рекомендации:** {{recommended_actions}} · ответственный: {{responsible}} · срок: {{due_date}}
- **Подтверждение человеком:** {{requires_human_review}} — {{human_review_reason}}

## 4. Риски

| Категория | Описание | Вероятность | Влияние |
|---|---|---|---|
| {{risk.category}} | {{risk.description}} | {{risk.likelihood}} | {{risk.impact}} |

## 5. Рекомендуемые корректирующие мероприятия

| Действие | Ответственный | Срок | Приоритет |
|---|---|---|---|
| {{action.action}} | {{action.responsible}} | {{action.due_date}} | {{action.priority}} |

## 6. Требует подтверждения специалистом

| Проблема | Причина | Критичность |
|---|---|---|
| {{issue_id}} | {{reason}} | {{severity}} |

## 7. Ограничения данных этого обхода

{{data_quality_notes}}

---

_{{disclaimer}}_
