# API реестра НОСТРОЙ — что работает (проверено 10.11.2026)

Базовый адрес `https://reestr.nostroy.ru/api/`. Все методы — **POST** с JSON-телом
(GET отвечает 405 «Allow: POST»). Маршруты взяты из JS сайта
(`/js/chunk-15115df2.*.js`: `sro/list`, `sro/{id}`, `sro/{id}/member/list`,
`sro/all/member/list`, `member/{id}/info`, `member/{id}/frame`,
`sro/{id}/register/generate`, `sro/{id}/register/download` и др.).

Тело для списков: `{"filters":{},"page":N,"pageCount":"500","searchString":"","sortBy":{}}`
(`pageCount` — строкой). Ответ: `data.data` — записи, `data.count` — сколько всего,
`data.countPages` — страниц.

## Где дата исключения

**Только в карточке члена:** `POST /api/member/{id}/info` → `data.suspension_date`
(ISO, напр. `"2025-09-05T00:00:00+03:00"`), основание — `data.suspension_reason`.
Та же дата дублируется в `data.right.actions[]` — элемент с
`suspension_decision.code == "4"` («Прекращение действия права»), поле `basis_date`;
остальные элементы с кодом 1 — приостановления права (их бывает много, это не исключение).

`{id}` — это `id` записи из любого списка членов (не ИНН и не номер в реестре СРО).

В списках (`sro/all/member/list` и `sro/{id}/member/list`) этого поля **нет вообще** —
поэтому полная выгрузка 10.11.2026 и не нашла дату у 276 тыс. исключённых. Нужно по
одному запросу карточки на каждого исключённого.

**Быстрый путь (им и собрана сводка):** кнопка «Выгрузить реестр членов СРО» —
`POST sro/{id}/register/generate` (ответ `{"success":true,"data":{"actualRegisterIsExists":true}}`),
затем `GET sro/{id}/register/download` → zip с `register-1-500.xlsx`, `register-501-1000.xlsx`…
Колонки (строка 2 — шапка): «N п/п» (кол. 2; строки без номера — продолжения
записи: проверки, страховки), «Регистрационный номер в реестре СРО», «Дата
регистрации в реестре СРО», **«Дата прекращения членства»**, «Основание
прекращения членства», «ОГРН/ОГРНИП», «ИНН». Статуса члена в xlsx нет — он берётся
из списка. Пара «строка архива ↔ запись списка» — по (ИНН, дата вступления, номер
в реестре СРО).

Проверено 10.11.2026 на 19 СРО Петербурга: все 27 080 записей нашли пару, у всех
18 114 исключённых в архиве есть дата прекращения; у 437 исключённых она сверена
с `suspension_date` карточки — совпала у всех 437. Архив сервер хранит готовым и
перегенерирует не каждый раз (даты файлов внутри — от 09.06.2026 до 10.11.2026),
поэтому для исключённого без даты в архиве скрипт берёт карточку (на 10.11.2026
таких 0).

`last_updated_at` записи как замена даты исключения **не годится**: в тот же день
приходится лишь у 3 453 из 18 114 исключённых (19 %), у 8 975 — позже больше чем
на 30 дней.

## Эндпоинты

| что | запрос | работает |
|---|---|---|
| список всех СРО | `POST sro/list` (тело списка) | да — 344 СРО, с `id`, `registration_number`, `state`, `region_name` |
| карточка СРО | `POST sro/{id}` (тело `{}`) | да: `full_description`, `short_description`, `inn`, `ogrn`, `registration_number`, `place`, `site`, `phone`, `email`. **Руководителя нет** (нет и в шапке xlsx-выгрузки) |
| все члены всех СРО | `POST sro/all/member/list` | да |
| выгрузка реестра СРО (xlsx в zip) | `POST sro/{id}/register/generate`, затем `GET sro/{id}/register/download` | да, ~1–4 запроса на 500 членов |
| члены одной СРО | `POST sro/{id}/member/list` | **да, работает** (запись «не работает у НОСТРОЯ» устарела); полнота по 19 СРО Петербурга — 100 % |
| карточка члена | `POST member/{id}/info` (тело `{}`) | да; адреса из `_MEMBER_CARD_URLS` (`/api/member/{id}`, `/api/sro/member/{id}` …) — 404 |

`id` СРО — номер в адресе `reestr.nostroy.ru/sro/{id}`, его даёт `sro/list` по
`registration_number`.

## Пример записи юрлица (обезличено, телефоны и e-mail убраны)

Из `sro/{id}/member/list`:

```json
{
  "registry_registration_date_time_string": "18.07.2022 00:00:00",
  "last_updated_at_date_time_string": "05.09.2025 15:17:55",
  "id": 5800000,
  "member_type": {"id": 1, "code": "1", "title": "ЮЛ"},
  "member_status": {"id": 2, "code": "2", "title": "Исключен"},
  "region_number": {"id": 77, "code": "77", "title": "Москва"},
  "full_description": "Общество с ограниченной ответственностью \"…\"",
  "short_description": "ООО \"…\"",
  "registration_number": "1787",
  "registry_registration_date": "2022-07-18T00:00:00+03:00",
  "compensation_fund_fee_odo": "0",
  "compensation_fund_fee_vv": "100000",
  "responsibility_level_vv": {"id": 1, "code": "1", "title": "Первый уровень ответственности",
                              "cost": "не превышает девяносто миллионов рублей"},
  "ogrnip": "118774600000X",
  "inn": "77160000XX",
  "sro": {"id": 85, "short_description": "Ассоциация «СРО «АЛЬЯНС СТРОИТЕЛЕЙ»"},
  "inventory_number": "С-018-0077160000XX-2637",
  "other_information": ""
}
```

Карточка `member/{id}/info` той же записи — дополнительно к полям списка (сокращено):

```json
{
  "address": {"index": "129…", "subject": "Москва", "full_address": "…"},
  "accordance_status": {"id": 2, "code": "2", "title": "Не соответствует"},
  "state_registration_date": "2018-03-02T00:00:00+03:00",
  "phones": "<убрано>",
  "director": "Генеральный директор <ФИО убрано>",
  "suspension_date": "2025-09-05T00:00:00+03:00",
  "suspension_reason": "На основании добровольного выхода из состава членов СРО в соответствии с ч.1 ст. 55.7 ГрК РФ",
  "checks": [{"check_date": "2025-06-27T00:00:00+03:00",
              "member_check_type": {"title": "Плановая"},
              "member_check_result": {"title": "Нарушения имеются"},
              "disciplinary_action": {"title": "Применялись"}}],
  "insurances": [],
  "right": {
    "right_status": {"id": 3, "code": "3", "title": "Прекращено"},
    "basis": "Протокол Президиума №… от 18.07.2022",
    "is_simple": true, "is_extremely_dangerous": false, "is_nuclear": false, "is_odo": false,
    "actions": [
      {"suspension_decision": {"id": 4, "code": "4", "title": "Прекращение действия права"},
       "basis": "На основании добровольного выхода …", "basis_date": "2025-09-05T00:00:00+03:00"},
      {"suspension_decision": {"id": 1, "code": "1", "title": "Приостановление действия права"},
       "basis": "На основании решения Дисциплинарной комиссии № …", "basis_date": "2025-08-21T00:00:00+03:00"}
    ]
  },
  "last_updated_at": "2025-09-05T15:17:55+03:00"
}
```
