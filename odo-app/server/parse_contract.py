"""Черновик карточки договора из текста документов — правилами, без ИИ.

Что умеет: номер, ИКЗ (из него ИНН/КПП заказчика), цена, НДС, сроки, стороны,
протокол торгов, закон закупки, предмет, адрес объекта, вид работ, сметы
(строки объектного расчёта, итог сводного), акты КС-3, ДС с новой ценой.
Всё, чего не нашёл, помечает в needs_review — человек дозаполняет в форме.
"""
from __future__ import annotations

import re

MONTHS = {"января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6, "июля": 7, "августа": 8,
          "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12}

LEGAL_FORMS = [
    (r"ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ", "ООО"), (r"Общество с ограниченной ответственностью", "ООО"),
    (r"АКЦИОНЕРНОЕ ОБЩЕСТВО", "АО"), (r"Акционерное общество", "АО"),
    (r"ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО", "ПАО"), (r"Публичное акционерное общество", "ПАО"),
    (r"ИНДИВИДУАЛЬНЫЙ ПРЕДПРИНИМАТЕЛЬ", "ИП"), (r"Индивидуальный предприниматель", "ИП"),
    (r"Государственное унитарное предприятие", "ГУП"), (r"ГОСУДАРСТВЕННОЕ УНИТАРНОЕ ПРЕДПРИЯТИЕ", "ГУП"),
    (r"Муниципальное унитарное предприятие", "МУП"), (r"МУНИЦИПАЛЬНОЕ УНИТАРНОЕ ПРЕДПРИЯТИЕ", "МУП"),
    (r"Государственное бюджетное дошкольное образовательное учреждение", "ГБДОУ"),
    (r"Государственное бюджетное общеобразовательное учреждение", "ГБОУ"),
    (r"Муниципальное бюджетное общеобразовательное учреждение", "МБОУ"),
    (r"Муниципальное бюджетное дошкольное образовательное учреждение", "МБДОУ"),
    (r"Государственное бюджетное учреждение", "ГБУ"), (r"Муниципальное казенное учреждение", "МКУ"),
]


def rub(x: float) -> str:
    return f"{x:,.2f}".replace(",", "\u00a0").replace(".", ",") + " ₽"


def num(s: str | None) -> float | None:
    if s is None:
        return None
    s = s.replace(" ", " ").replace(" ", "").replace(",", ".")
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def short_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip(" ,;")
    for pat, abbr in LEGAL_FORMS:
        name = re.sub(pat, abbr, name)
    name = re.sub(r'"([^"]+)"', r"«\1»", name)
    return name.strip()


def date_iso(s: str | None) -> str | None:
    if not s:
        return None
    m = re.search(r"(\d{1,2})\.(\d{2})\.(\d{4})", s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{int(m.group(1)):02d}"
    m = re.search(r"«?(\d{1,2})»?\s*([а-я]+)\s*(\d{4})", s)
    if m and m.group(2) in MONTHS:
        return f"{m.group(3)}-{MONTHS[m.group(2)]:02d}-{int(m.group(1)):02d}"
    return None


# ------------------------------------------------------------------ договор
LEGAL_START = (r"(?:Государственн\w+|Муниципальн\w+|Федеральн\w+|Санкт-Петербургск\w+|Общество\s+с\s+ограниченной|Акционерное\s+общество|"
               r"Публичное\s+акционерное|Непубличное\s+акционерное|Индивидуальн\w+\s+предпринимател\w+|Некоммерческ\w+|Автономн\w+|Региональн\w+|"
               r"Фонд\b|Администраци\w+|Комитет\b|Управлени\w+|Департамент\b|Министерств\w+|Учреждени\w+|Товариществ\w+|Жилищн\w+|"
               r"ООО\b|АО\b|ПАО\b|ГУП\b|МУП\b|ИП\b|ГБОУ\b|ГБДОУ\b|ГБУ\b|ГКУ\b|ГАУ\b|МБОУ\b|МБДОУ\b|МКУ\b|МАУ\b|ФГБУ\b|ФГУП\b|ФКУ\b|СПб\s+ГБУ)")
MONTH_RE = r"(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)"


def _org(s: str) -> str:
    """Начало наименования организации внутри куска преамбулы: от последней организационно-правовой формы."""
    s = s.strip(" ,;:—–-")
    # «(сокращённое наименование — ГУП «X»)» и «(ООО «X»)» — повтор полного имени, убираем до поиска начала
    s = re.sub(r"\s*\((?:сокращ[^)]*|[А-ЯA-Z]{2,5}\s*[«\"][^)]*)\)", "", s)
    last = None
    for m in re.finditer(LEGAL_START, s):
        last = m
    if last:
        s = s[last.start():]
    s = s.split(" в лице")[0].split(", именуем")[0]
    return short_name(s).strip(" ,;)")


def parse_contract_text(t: str) -> tuple[dict, dict]:
    """→ (поля договора, подсказки 'откуда взято').

    Текст может прийти из docx (ровные строки) или из распознанного скана (строки рвутся где попало,
    попадаются «_», «—» и лишние пробелы). Поэтому почти всё ищется по «плоской» копии, где любые
    пробелы и переносы схлопнуты в один пробел.
    """
    f, hints = {}, {}
    flat = re.sub(r"[ \t\u00a0]*\n[ \t\u00a0]*", " ", t)
    flat = re.sub(r"[ \t\u00a0]+", " ", flat)
    flat = re.sub(r"={3,}\s*стр\.\s*\d+\s*={3,}", " ", flat)   # маркеры страниц из OCR
    head = flat[:6000]

    m = re.search(r"(?:КОНТРАКТ|ДОГОВОР|Контракт|Договор)[^№]{0,80}?№\s*([^\s,;)]+)", head)
    if m:
        f["number"] = m.group(1).strip("«»\"_")
        hints["number"] = "заголовок документа"

    m = re.search(r"код\s+закупки[\s:\-–—_]*(\d{36})", flat[:12000], re.I)
    if m:
        f["ikz"] = m.group(1)
        f["customer_inn"] = m.group(1)[3:13]
        f["customer_kpp"] = m.group(1)[13:22]
        hints["customer_inn"] = "из ИКЗ (знаки 4–13)"
        f["procurement_law"] = "44-fz"

    # дата: «13» марта 2025 / 18.05.2026 в шапке до преамбулы; «__2026» — не заполнена.
    # Даты законов («от 05.04.2013 №44-ФЗ») отсекаются: за ними идёт «№».
    cut = re.search(r"именуем", head)
    top = head[: cut.start()] if cut else head[:700]
    m = re.search(r"«?\s*(\d{1,2})\s*»?[\s_]*" + MONTH_RE + r"[\s_]*(\d{4})(?!\s*[№N])", top)
    if m:
        f["date"] = date_iso(f"{m.group(1)} {m.group(2)} {m.group(3)}")
        hints["date"] = "шапка договора"
    else:
        m = re.search(r"(?<![\d.])(\d{2}\.\d{2}\.\d{4})(?![\d.])(?!\s*(?:г\.\s*)?[№N])", top)
        if m:
            f["date"] = date_iso(m.group(1))
            hints["date"] = "шапка договора"
    if not f.get("date") and re.search(r"_{2,}\s*20\d\d", top):
        f["date"] = None
        hints["date"] = "дата в тексте не заполнена (проект из ЕИС)"

    # цена: «Цена контракта составляет 8480267 рублей 44 копеек» / «… является твёрдой … и составляет 768 333 211 (прописью) рублей 08 копеек»
    price_seg = None
    for pat in (r"Цена\s+(?:контракта|договора)[^.]{0,220}?составляет\s*([\d\s]{1,20}?\d)\s*(?:\([^)]{0,400}\))?\s*руб\w*\s*(\d{2})\s*коп",
                r"Цена\s+(?:контракта|договора)[^.]{0,220}?составляет\s*([\d\s]{1,20}?\d)\s*(?:\([^)]{0,400}\))?\s*руб"):
        m = re.search(pat, flat, re.I)
        if m:
            kop = m.group(2) if m.lastindex and m.lastindex >= 2 else "00"
            f["price_rub"] = num(m.group(1) + "." + kop)
            hints["price_rub"] = "п. «Цена контракта»"
            price_seg = flat[max(0, m.start() - 50): m.end() + 500]
            break
    if f.get("price_rub") is None:
        m = re.search(r"(?:стоимость|цена)\s+(?:работ|договора|контракта)[^\d]{0,80}?([\d\s]{5,}[,.]\d{2})\s*(?:руб|₽)", flat, re.I)
        if m:
            f["price_rub"] = num(m.group(1))
            hints["price_rub"] = "раздел о цене"
            price_seg = flat[max(0, m.start() - 50): m.end() + 500]
    if price_seg:
        if re.search(r"НДС\s+не\s+облага|без\s+НДС", price_seg, re.I):
            f["price_includes_vat"] = False
        elif re.search(r"с\s+уч[её]том\s+(?:налога\s+на\s+добавленную\s+стоимость|НДС)|включая\s+НДС|в\s+том\s+числе\s+НДС", price_seg, re.I):
            f["price_includes_vat"] = True

    # НМЦК: через обеспечение («10 % от НМЦК, что составляет N») или прямо («начальная (максимальная) цена … составляет N руб»)
    m = re.search(r"начальн\w+\s+\(?максимальн\w+\)?\s+цен\w+\s+(?:контракта|договора)?\s*(?:составляет|равна|[:—–-])\s*([\d\s]{4,}?\d)\s*(?:\([^)]{0,300}\))?\s*руб\w*\s*(\d{2})?", flat, re.I)
    if m:
        f["nmck_rub"] = num(m.group(1) + "." + (m.group(2) or "00"))
        hints["nmck_rub"] = "упоминание начальной (максимальной) цены в договоре"
    else:
        m = re.search(r"(\d{1,2})\s*%\s*от\s+начальн\w+\s+\(?максимальн\w+\)?\s+цены\s+контракта,?\s*что\s+составляет\s*([\d\s]{4,}?\d)\s*(?:\([^)]{0,300}\))?\s*руб\w*\s*(\d{2})?", flat, re.I)
        if m:
            amt = num(m.group(2) + "." + (m.group(3) or "00"))
            if amt:
                f["nmck_rub"] = round(amt * 100 / int(m.group(1)), 2)
                hints["nmck_rub"] = f"расчёт: обеспечение {m.group(1)} % от НМЦК = {amt:,.2f} ₽ (пункт об обеспечении исполнения контракта)".replace(",", " ")

    # сроки
    m = re.search(r"начал\w+\s+выполнения\s+работ[^:.]{0,60}?[:—–-]?\s*(?:с\s*)?(\d{2}\.\d{2}\.\d{4}|«?\s*\d{1,2}\s*»?\s*[а-я]+\s*\d{4})", flat, re.I)
    if m:
        f["period_from"] = date_iso(m.group(1))
    else:
        m = re.search(r"начальн\w+\s+срок\s+выполнения\s+работ[^.]{0,80}?с\s+" + MONTH_RE + r"\s+(\d{4})", flat, re.I)
        if m:
            f["period_from"] = f"{m.group(2)}-{MONTHS[m.group(1)]:02d}-01"
            hints["period_from"] = "«с месяца» — взято первое число"
    m = re.search(r"окончани\w+\s+выполнения\s+работ[^:.]{0,60}?[:—–-]?\s*(?:по\s*|до\s*)?(\d{2}\.\d{2}\.\d{4}|«?\s*\d{1,2}\s*»?\s*[а-я]+\s*\d{4})", flat, re.I)
    if m:
        f["period_to"] = date_iso(m.group(1))
    else:
        m = re.search(r"конечн\w+\s+срок\s+выполнения\s+работ[^.]{0,80}?(\d{1,3})\s*\([^)]*\)\s*(?:календарн\w+\s+)?(месяц\w*|дн\w*)", flat, re.I)
        if m and f.get("period_from"):
            import datetime as _dt
            d0 = _dt.date.fromisoformat(f["period_from"])
            n = int(m.group(1))
            if m.group(2).startswith("мес"):
                mm = d0.month - 1 + n
                d1 = _dt.date(d0.year + mm // 12, mm % 12 + 1, min(d0.day, 28))
            else:
                d1 = d0 + _dt.timedelta(days=n)
            f["period_to"] = d1.isoformat()
            hints["period_to"] = f"{n} {m.group(2)} с начала работ — расчётно"

    # стороны
    pre = re.search(r"(?P<a>.{2,700}?),?\s*именуем\w*\s+в\s+дальнейшем\s*[–—-]?\s*[«\"]?(?P<ra>Заказчик|Генподрядчик|Генеральный подрядчик|Застройщик|Технический заказчик)[»\"]?"
                    r".*?с\s+одной\s+стороны,?\s+и\s+(?P<b>.{5,500}?)(?:,?\s*именуем\w*\s+в\s+дальнейшем\s*[–—-]?\s*[«\"]?(?P<rb>Подрядчик|Субподрядчик|Генподрядчик|Исполнитель)[»\"]?|\s+в\s+лице)", flat, re.S)
    if pre:
        f["customer_name"] = _org(pre.group("a"))
        f["customer_role_word"] = pre.group("ra")
        f["contractor_name"] = _org(pre.group("b"))
        f["contractor_role_word"] = pre.group("rb") or "Подрядчик"
        hints["customer_name"] = "преамбула"
        hints["contractor_name"] = "преамбула"

    # протокол торгов и закон
    m = re.search(r"протокол\w*\s*№\s*([\d\-/A-Za-zА-Яа-я]+)\s*от\s*(\d{2}\.\d{2}\.\d{4})", flat, re.I)
    if m:
        f["protocol"] = f"протокол № {m.group(1)} от {m.group(2)}"
    if re.search(r"44-ФЗ|О контрактной системе", flat):
        f["procurement_law"] = "44-fz"
    elif re.search(r"223-ФЗ|о закупках товаров, работ, услуг отдельными видами юридических лиц", flat, re.I):
        f["procurement_law"] = "223-fz"
    tender_words = re.search(r"по\s+(?:итогам|результатам)\s+(?:проведения\s+)?(?:электронн\w+\s+)?(?:аукцион|конкурс|торг|закупк|тендер)|победител\w+\s+закупки|коэффициент\w*\s+аукционного\s+снижения", flat, re.I)
    if f.get("procurement_law") in ("44-fz", "223-fz"):
        f["procurement"] = "competitive"
        if re.search(r"единственн\w+\s+(?:поставщик|подрядчик)\w*\s*(?:\(|,)?\s*(?:подрядчик\w*|исполнител\w*)?[^.]{0,80}?(?:п\.|пункт\w*)\s*\d{1,2}\s*(?:ч\.|части)\s*1\s*(?:ст\.|статьи)\s*93", flat, re.I) and not tender_words:
            f["procurement"] = "direct"
            hints["procurement"] = "ссылка на закупку у единственного поставщика (п. … ч. 1 ст. 93 44-ФЗ)"
    elif tender_words:
        f["procurement"] = "competitive"
        f["procurement_law"] = "unknown"
    elif re.search(r"единственн\w+\s+поставщик|без\s+проведения\s+торгов", flat, re.I):
        f["procurement"] = "direct"
    else:
        f["procurement"] = "unknown"
    if f.get("procurement") == "competitive" and "procurement" not in hints:
        bits = [f.get("protocol"), {"44-fz": "ссылки на 44-ФЗ", "223-fz": "ссылки на 223-ФЗ"}.get(f.get("procurement_law")),
                ("ИКЗ " + f["ikz"]) if f.get("ikz") else None, ("«" + tender_words.group(0) + "»") if tender_words else None,
                "сноска о цене «по итогам проведения электронного конкурса»" if re.search(r"по\s+итогам\s+проведения\s+электронного\s+конкурса", flat, re.I) else None]
        hints["procurement"] = "; ".join(x for x in bits if x)

    # предмет и объект
    m = re.search(r"(?<![\d.])1\.1\.\s*(.+?)(?=\s(?<![\d.])1\.2\.|$)", flat)
    if m:
        f["subject_text"] = m.group(1).strip()[:1200]
    m = re.search(r"Место\s+(?:нахождения\s+объекта|выполнени\w+\s+работ)[^:]{0,60}:\s*(.+?)(?=\s(?<![\d.])\d\.\d{1,2}\.|\*|$)", flat, re.I)
    if m:
        f["object_address"] = m.group(1).strip(" .*")[:300]
    m = re.search(r"Результатом\s+(?:выполненной\s+)?работ\w*[^.]*?являе?тся\s+(.+?)(?=\s(?<![\d.])\d\.\d{1,2}\.|$)", flat, re.I)
    if m:
        f["result_text"] = m.group(1).strip()[:600]

    # вид работ: сначала по предмету (п. 1.1 / заголовок), потом по началу текста; строительство и реконструкция — по первому упоминанию
    subj = (f.get("subject_text") or "") + " " + head[:1500]
    low = subj.lower()
    order = [("капитальн\\w+\\s+ремонт", "capital_repair"), ("текущ\\w+\\s+ремонт", "current_repair"), ("реконструкци", "reconstruction"),
             ("\\bснос\\w*\\b|демонтаж\\w*\\s+здани", "demolition"), ("проектн\\w+\\s+документаци|разработк\\w+\\s+проект", "design"),
             ("инженерн\\w+\\s+изыскан", "survey"), ("строительств\\w*", "construction"), ("\\bремонт", "repair_unspecified")]
    found = [(mm.start(), wt) for pat, wt in order for mm in [re.search(pat, low)] if mm]
    if found:
        # капремонт/текущий ремонт побеждают, если названы; иначе — что встретилось раньше
        prio = [wt for _, wt in found if wt in ("capital_repair", "current_repair")]
        f["work_type"] = prio[0] if prio else min(found)[1]
    else:
        f["work_type"] = "unknown"

    m = re.search(r"\((\d\d\.\d\d\.\d\d\.\d{3})\)", flat)
    if m:
        f["okpd2"] = m.group(1)
    f["mentions_sro"] = bool(re.search(r"саморегулируем|\bСРО\b", flat))
    f["requires_sro_membership"] = bool(re.search(r"(?:должен|обязан)\s+являться\s+членом\s+саморегулируемой", flat, re.I))
    return f, hints


# ------------------------------------------------------------------ сметы
def parse_estimates(texts: list[str]) -> dict:
    """Строки объектного сметного расчёта и итоги сводного."""
    out = {"lines": [], "object_total": None, "summary_total": None, "vat_pct": None, "unforeseen_pct": None, "methodology_421": False, "summary_header_total": None}
    for t in texts:
        if re.search(r"приказ\w*\s+№?\s*421", t, re.I) or "421/пр" in t:
            out["methodology_421"] = True
        m = re.search(r"НДС\s*[-–—]?\s*(\d{1,2})\s*%", t)
        if m:
            out["vat_pct"] = int(m.group(1))
        m = re.search(r"Непредвиденные\s+затраты[^%]{0,160}?(\d{1,2})\s*%", t, re.I | re.S)
        if m:
            out["unforeseen_pct"] = int(m.group(1))
        # объектный расчёт: код / наименование / числа
        if re.search(r"ОБЪЕКТН\w+\s+СМЕТН\w+\s+РАСЧ", t, re.I):
            m = re.search(r"Сметная\s+стоимость\s*\n?\s*([\d\s ]+[,.]\d{2})\s*руб", t)
            if m:
                out["object_total"] = num(m.group(1))
            lines = [ln.strip() for ln in t.splitlines()]
            i = 0
            while i < len(lines):
                if re.fullmatch(r"\d\d-\d\d-\d\d", lines[i]) and i + 1 < len(lines):
                    code, name = lines[i], lines[i + 1]
                    nums = []
                    k = i + 2
                    while k < len(lines) and re.fullmatch(r"[\d\s ]+[,.]\d{2}", lines[k]):
                        nums.append(num(lines[k]))
                        k += 1
                    # у строки колонки: строительные / монтажные / оборудование / прочие / всего;
                    # «всего» = сумма предыдущих (или повтор единственной колонки). Дальше идут итоги — не наши.
                    total, used = (nums[0], 1) if nums else (None, 0)
                    if len(nums) >= 2 and abs(nums[1] - nums[0]) < 0.011:
                        total, used = nums[0], 2
                    else:
                        for j in range(2, len(nums)):
                            if abs(sum(nums[:j]) - nums[j]) < 0.011:
                                total, used = nums[j], j + 1
                                break
                    if total is not None and name and not re.fullmatch(r"[\d\s,.]+", name):
                        out["lines"].append({"code": code, "name": f"{name} ({code})", "amount_rub": total, "source": "объектный сметный расчёт"})
                    i = i + 2 + used
                else:
                    i += 1
        # сводный расчёт
        if re.search(r"СВОДН\w+\s+СМЕТН\w+\s+РАСЧ", t, re.I):
            m = re.search(r"сметной\s+стоимостью\s*([\d\s ]+[,.]\d{2})\s*руб", t, re.I)
            if m:
                out["summary_header_total"] = num(m.group(1))
            nums = [num(x) for x in re.findall(r"(?m)^\s*([\d\s ]{7,}[,.]\d{2})\s*$", t)]
            nums = [x for x in nums if x]
            if nums:
                out["summary_total"] = max(nums)
    if out["lines"]:
        s = round(sum(x["amount_rub"] for x in out["lines"]), 2)
        out["lines_sum"] = s
        if out["object_total"] and abs(s - out["object_total"]) > 1:
            out["lines_mismatch"] = True
    return out


def parse_acts(texts: list[str]) -> dict:
    """КС-3 / КС-2 / документы о приёмке: суммы «Итого» с НДС."""
    total, found = 0.0, 0
    for t in texts:
        for m in re.finditer(r"(?:Всего\s+с\s+учетом\s+НДС|Всего\s+по\s+акту|ИТОГО\s+с\s+НДС|Итого\s+к\s+оплате)[^\d\n]{0,40}([\d\s ]+[,.]\d{2})", t, re.I):
            v = num(m.group(1))
            if v:
                total += v
                found += 1
                break
    return {"executed_rub": round(total, 2) if found else None, "acts_found": found}


def parse_addenda(texts: list[str]) -> list[dict]:
    out = []
    for t in texts:
        m = re.search(r"Дополнительн\w+\s+соглашени\w+\s*№\s*(\S+)", t, re.I)
        number = m.group(1) if m else "б/н"
        d = re.search(r"(\d{2}\.\d{2}\.\d{4})", t[:800])
        pm = re.search(r"Цена\s+(?:контракта|договора)\s+составляет\s*([\d\s ]+)\s*руб\w*\s*(\d{2})?", t, re.I)
        price = num(pm.group(1) + "." + (pm.group(2) or "00")) if pm else None
        note = "меняет цену" if price else ("реквизиты / прочее" if re.search(r"реквизит|банк", t, re.I) else "без изменения цены")
        if re.search(r"срок\w*\s+выполнения", t, re.I) and not price:
            note = "меняет сроки"
        out.append({"number": number, "date": date_iso(d.group(1)) if d else None, "price_rub": price, "note": note})
    return out


# ------------------------------------------------------------------ карточка
def customer_kind_guess(name: str | None, work_type: str | None = None) -> tuple[str, str]:
    n = (name or "").lower()
    if not n:
        return "unknown", ""
    building = work_type in ("construction", "reconstruction", "demolition")
    if re.search(r"фонд\w*\s+капитальн\w+\s+ремонт|региональн\w+\s+оператор", n):
        return "regional_operator", "региональный оператор капитального ремонта — по наименованию"
    if re.search(r"специализированн\w+\s+застройщик|\bсз\b", n):
        return "developer", "специализированный застройщик — по наименованию; проверить разрешение на строительство"
    if re.search(r"техническ\w+\s+заказчик", n):
        return "technical_customer", "по наименованию; проверить договор с застройщиком"
    if re.search(r"учреждени|гбоу|гбдоу|гбу|мбоу|мбдоу|мку|мау|гку|гау|казенн|бюджетн|автономн|администраци|комитет|управлени|министерств|департамент|унитарн\w+\s+предприяти|\bгуп\b|\bмуп\b|водоканал|теплосет|тепловые сети|электросет", n):
        if building:
            return "developer", "государственное/муниципальное предприятие, учреждение или орган строит (реконструирует) объект для себя: обеспечивает строительство на своём участке, получает разрешения на строительство и ввод — застройщик (п. 16 ст. 1 ГрК РФ); разрешение на строительство и право на участок не проверялись"
        return "operator", "государственное/муниципальное учреждение, предприятие или орган: здание закреплено на праве оперативного управления или хозяйственного ведения — лицо, ответственное за эксплуатацию (ч. 1 ст. 55.25 ГрК РФ); право по выписке ЕГРН не проверялось"
    if re.search(r"генеральн\w+\s+подрядчик|генподряд|строй|строительн", n):
        return "general_contractor", "похоже на подрядную организацию — вероятен субподряд; проверить"
    return "unknown", ""


def build_card(member: dict, docs: list[dict]) -> tuple[dict, dict]:
    """docs: [{filename, kind, text}] → (card, draft_meta)."""
    texts = {k: [d["text"] for d in docs if d["kind"] == k] for k in ("contract", "estimate", "act", "addendum", "letter", "other")}
    warnings, needs = [], []
    f, hints = parse_contract_text(texts["contract"][0]) if texts["contract"] else ({}, {})
    if not texts["contract"]:
        warnings.append("Договор среди файлов не распознан: заполните карточку вручную.")
    est = parse_estimates(texts["estimate"] + texts["other"])
    acts = parse_acts(texts["act"])
    addenda = parse_addenda(texts["addendum"])

    price = f.get("price_rub")
    for a in addenda:
        if a.get("price_rub"):
            price = a["price_rub"]
    wt = f.get("work_type", "unknown")
    ckind, ckind_basis = customer_kind_guess(f.get("customer_name"), wt)
    wt_basis = None
    if wt == "repair_unspecified":
        if est["methodology_421"]:
            wt, wt_basis = "capital_repair", "в договоре — «ремонт» без уточнения; сметы составлены по Методике 421/пр (сводный сметный расчёт, глава 2 «…капитального ремонта», непредвиденные затраты по п. 179) — это капитальный ремонт объекта капитального строительства"
        else:
            wt, wt_basis = "unknown", "в договоре — «ремонт» без уточнения; по сметам характер работ не установлен"
            needs.append("work_type")
    elif wt == "unknown":
        needs.append("work_type")

    kind = {"design": "design", "survey": "survey", "demolition": "demolition"}.get(wt, "construction")
    number = f.get("number") or ""
    works = [{"name": ln["name"], "amount_rub": ln["amount_rub"], "source": ln["source"], "human_decision": None} for ln in est["lines"]]

    price_basis = []
    if price is not None:
        price_basis.append(f"{hints.get('price_rub', 'цена')}: {rub(price)}")
    if est.get("summary_total") and price is not None:
        if abs(est["summary_total"] - price) < 1:
            price_basis.append("итог сводного сметного расчёта совпадает с ценой договора")
        else:
            price_basis.append(f"итог сводного сметного расчёта {rub(est['summary_total'])} не совпадает с ценой договора")
            warnings.append("Итог сводного сметного расчёта не совпадает с ценой договора — проверьте, какая версия сметы приложена.")
    if est.get("summary_header_total") and est.get("summary_total") and abs(est["summary_header_total"] - est["summary_total"]) > 1:
        warnings.append(f"В шапке сводного расчёта указана сумма {rub(est['summary_header_total'])}, а итог расчёта — {rub(est['summary_total'])}: расхождение в документе заказчика.")
    if est.get("lines_mismatch"):
        warnings.append("Сумма строк объектного расчёта не сходится с его итогом — проверьте распознанные строки.")
    if addenda:
        price_basis.append("ДС: " + "; ".join(f"№ {a['number']} — {a['note']}" for a in addenda))

    if not f.get("customer_name"):
        needs.append("customer_name")
    if ckind == "unknown":
        needs.append("customer_kind")
    if price is None:
        needs.append("price_rub")
    if f.get("procurement") == "unknown":
        needs.append("procurement")
    if f.get("procurement_law") == "unknown":
        needs.append("procurement_law")
    if not works:
        warnings.append("Строки смет не распознаны: доля работ по Перечню 624 считаться не будет (на вывод об ОДО это не влияет).")
    if not f.get("date"):
        warnings.append("Дата договора не найдена или не заполнена — для реестра укажите дату подписания.")
    if texts["contract"] and f.get("requires_sro_membership"):
        warnings.append("Договор прямо требует от подрядчика членства в СРО — заказчик сам считал закупку конкурентной с обязательным членством.")
    elif texts["contract"] and f.get("mentions_sro"):
        warnings.append("В договоре упоминается СРО — посмотрите, что именно требовал заказчик.")
    if price is not None and price <= 10_000_000 and f.get("procurement") == "competitive" and not f.get("nmck_rub"):
        warnings.append("Цена ниже 10 млн, торги: начальная цена закупки в договоре не найдена. Если в ЕИС она была выше 10 млн — случай спорный, укажите её в карточке.")

    card = {
        "schema_version": "1",
        "member": {"name": member.get("name") or f.get("contractor_name") or "", "inn": member.get("inn"), "role": "contractor",
                   "is_state_entity": False, "sro_kinds": member.get("sro_kinds") or ["build"], "membership_date": None},
        "contract": {
            "number": number, "date": f.get("date"),
            "subject_text": (f.get("subject_text") or "") + ((" " + f["result_text"]) if f.get("result_text") else ""),
            "kind": kind, "kind_basis": _kind_basis(f, est), "mixed_parts": [],
            "price_rub": price, "price_basis": "; ".join(price_basis) or None, "price_includes_vat": f.get("price_includes_vat"),
            "addenda": addenda, "status": "completed" if acts.get("executed_rub") and price and acts["executed_rub"] >= price - 1 else "active",
            "status_basis": _status_basis(f, acts), "period_from": f.get("period_from"), "period_to": f.get("period_to"),
            "procurement": f.get("procurement", "unknown"), "procurement_basis": hints.get("procurement") or None,
            "nmck_rub": f.get("nmck_rub"), "nmck_basis": hints.get("nmck_rub"),
            "procurement_law": f.get("procurement_law") if f.get("procurement_law") in ("44-fz", "223-fz", "mandatory_tender", "voluntary_tender") else ("unknown" if f.get("procurement") == "competitive" else None),
            "executed_rub": acts.get("executed_rub"), "executed_basis": (f"по актам: {acts['acts_found']} шт." if acts.get("executed_rub") else None),
            "has_final_act": None, "termination_document": None,
        },
        "customer": {"name": f.get("customer_name") or "", "inn": f.get("customer_inn"), "kind": ckind, "kind_basis": ckind_basis or None},
        "object": {"name": _object_name(f), "address": f.get("object_address"), "cadastral": None, "is_capital": True if wt in ("capital_repair", "construction", "reconstruction", "demolition") else None,
                   "permit_required": False if wt == "capital_repair" else None, "housing_type": "none", "category": "ordinary",
                   "basis": _object_basis(f, wt, est)},
        "work_type": wt if wt in ("construction", "reconstruction", "capital_repair", "demolition", "current_repair", "improvement", "design", "survey", "mixed", "unknown") else "unknown",
        "works": works,
        "sources": [{"file": d["filename"], "kind": d["kind"], "pages": None, "extraction_confidence": 0.9 if d.get("text") else 0.0} for d in docs],
        "as_of": None, "notes": None,
    }
    if wt_basis:
        card["object"]["basis"] = (card["object"]["basis"] or "") + " " + wt_basis
    meta = {"needs_review": needs, "warnings": warnings, "hints": hints, "estimates": {k: v for k, v in est.items() if k != "lines"}, "acts": acts, "source": "rules"}
    return card, meta


def _kind_basis(f, est):
    parts = []
    if f.get("subject_text"):
        parts.append("п. 1.1: подрядчик выполняет работы и передаёт результат заказчику")
    if f.get("result_text"):
        parts.append("результат работ — овеществлённый, на объекте: строительный подряд (ст. 740 ГК РФ), капитальный ремонт охватывается им (п. 2 ст. 740)")
    if f.get("okpd2"):
        parts.append(f"код закупки ОКПД2 {f['okpd2']}")
    if est.get("lines"):
        parts.append(f"объектный сметный расчёт: {len(est['lines'])} локальных смет" + (f", итого {rub(est['object_total'])} без НДС" if est.get("object_total") else ""))
    return "; ".join(parts) or None


def _status_basis(f, acts):
    p = []
    if f.get("period_from") or f.get("period_to"):
        p.append(f"срок работ {f.get('period_from') or '?'} – {f.get('period_to') or '?'}")
    p.append(f"актов приёмки: {acts['acts_found']}" if acts.get("acts_found") else "документов о приёмке в пакете нет")
    return "; ".join(p)


def _object_name(f):
    cn = f.get("customer_name")
    if f.get("result_text"):
        return f"Здание: {f.get('object_address') or cn or 'объект по договору'}"
    return f.get("object_address") or (f"Объект заказчика {cn}" if cn else "Объект по договору")


def _object_basis(f, wt, est):
    p = []
    if wt == "capital_repair":
        p.append("капитальный ремонт объекта капитального строительства: разрешение на строительство не требуется (ч. 17 ст. 51 ГрК РФ), но обязательное членство сохраняется")
    if est.get("methodology_421"):
        p.append("сметы по Методике 421/пр (приказ Минстроя от 04.08.2020)")
    p.append("категория объекта — обычный (не ст. 48.1 ГрК РФ), если в карточке не отмечено иное")
    return "; ".join(p)
