# Логика расчёта отклонений

Все числовые выводы Schedule Control Agent считаются **обычной арифметикой**
(`scripts/deviation.py`), а не «на глаз» моделью. Модель поставляет только
`actual_percent` (из наблюдений). Ниже — определения и формулы.

## Обозначения

- `S` — плановый старт задачи (`ScheduleTask.planned_start`).
- `F` — плановый финиш (`ScheduleTask.planned_finish`).
- `D` — дата обхода (`Inspection.date`, поле `as_of_date`).
- `A` — фактическая готовность, % (`ProgressObservation.estimated_completion_percent`).
- `P` — плановая готовность на дату `D`, %.

## 1. Плановая готовность `P` (planned percent)

Линейная модель освоения (достаточно для MVP; при наличии — использовать
план-график освоения/весов):

```
если D < S:            P = 0
если D > F:            P = 100
если S ≤ D ≤ F:        P = 100 * (D − S) / (F − S)     // дни
```

Если задача разбита по помещениям и известны объёмы (`EstimateItem.quantity`),
`P` можно взвешивать по объёму на помещение; иначе — равномерно.

## 2. Отклонение `deviation_percent`

```
deviation_percent = A − P
```
- `< 0` — отставание; `> 0` — опережение; около 0 — в графике (порог ±5 п.п.).

## 3. Просрочка в днях `days_overdue`

Через «дату, к которой план ожидал достигнутый факт `A`»:

```
date_planned_for_A = S + (A / 100) * (F − S)
days_overdue       = D − date_planned_for_A        // в днях, округление вниз
```
- `> 0` — работа отстаёт на столько дней; `= 0` — в графике; `< 0` — с опережением.
- Частный случай: если план требует 100% (`D ≥ F`), а `A < 100`, то
  `days_overdue = D − F` как минимум (просрочка финиша).

## 4. Темп и прогноз завершения `forecast_finish`

По двум последним обходам `D₁ (A₁)` и `D₂ (A₂)`:

```
rate = (A₂ − A₁) / (D₂ − D₁)            // %/день
если rate > 0:  forecast_finish = D₂ + (100 − A₂) / rate  дней
если rate ≤ 0:  forecast_finish = null  (работа стоит → риск, на человека)
```
Если обход один, `rate` берётся из плана как ориентир и помечается низким
`confidence`.

## 5. Флаг статуса `status_flag`

```
not_observed        — нет наблюдения по задаче в этом обходе
ahead               — deviation_percent > +порог
on_track            — |deviation_percent| ≤ порог (по умолчанию 5 п.п.)
behind              — deviation_percent < −порог, но D ≤ F
overdue             — D > F и A < 100
premature_start     — A > 0, но (D < S) или предшественник не завершён
sequence_violation  — нарушение технологической последовательности (см. ниже)
```

## 6. Преждевременный старт

`premature_start`, если `A > 0` и выполняется хотя бы одно:
- `D < S` (работа началась раньше планового старта);
- существует предшественник `pred` с типом `FS`, у которого
  `actual_percent < 100` (не `visually_complete`).

## 7. Технологическая последовательность

Для каждой связи `task ← predecessor` (`ScheduleTask.predecessor_ids`,
`dependency_type`):

```
FS (окончание→начало):  нарушение, если A(task) > 0 и A(pred) < 100
SS (начало→начало):     нарушение, если A(task) > 0 и A(pred) = 0
FF (окончание→окончание):нарушение, если A(task) = 100 и A(pred) < 100
```
Нарушение → запись в `sequence_checks(violation=true)` и `Issue(issue_kind =
sequence_violation)`. Для скрытых работ нарушение последовательности почти всегда
`severity ≥ high` (нельзя закрывать следующий слой поверх непринятого скрытого).

## 8. Влияние на последующие работы

- Отставание задачи `t` на `days_overdue` дней транслируется на её преемников:
  прямой обход по графу зависимостей, задержка распространяется по цепочке с
  учётом запасов (float, если известны). Затронутые → `impacted_schedule_task_ids`.
- Если `t` на критическом пути (float = 0) → сдвиг общего срока проекта на
  `days_overdue`; заметка в `critical_path_note`.

## 9. Критичность `severity` (эвристика)

```
critical — скрытые работы с нарушением/непроверенные; отставание задачи крит.
           пути > порога; риск срыва вехи договора со штрафом
high     — overdue или behind с days_overdue > 7; sequence_violation
medium   — behind в пределах запаса; days_overdue 1..7
low      — незначительное отклонение в пределах порога
info     — справочные наблюдения
```
Пороги (5 п.п., 7 дней и т.п.) — конфигурируемые параметры проекта.

## 10. Уверенность результата

`Issue.confidence` = min(confidence наблюдения `A`, качество привязки к задаче,
полнота покрытия помещения). Низкая уверенность (< 0.5) **всегда**
`requires_human_review = true`, даже при малой критичности.

## Псевдокод (ядро)

```python
def evaluate_task(task, obs, as_of, prev_obs=None):
    P = planned_percent(task.S, task.F, as_of)     # §1
    A = obs.actual_percent
    dev = A - P                                     # §2
    days = days_overdue(task.S, task.F, A, as_of)   # §3
    rate, forecast = forecast_finish(prev_obs, obs) # §4
    flag = status_flag(dev, as_of, task, A)         # §5-6
    seq = sequence_ok(task, deps_actuals)           # §7
    impacted = propagate_delay(task, days, graph)   # §8
    sev = severity(task, flag, days, seq)           # §9
    return TaskEvaluation(P, A, dev, days, forecast, flag, impacted, sev, ...)
```

Полная реализация — `scripts/deviation.py`.
