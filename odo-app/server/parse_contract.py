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
def parse_contract_text(t: str) -> tuple[dict, dict]:
    """→ (поля договора, подсказки 'откуда взято')."""
    f, hints = {}, {}
    head = t[:6000]

    m = re.search(r"(?:КОНТРАКТ|ДОГОВОР|Контракт|Договор)[^\n№]{0,60}№\s*([^\s\n,;]+)", head)
    if m:
        f["number"] = m.group(1).strip("«»\"")
        hints["number"] = "заголовок документа"

    m = re.search(r"код\s+закупки:?\s*(\d{36})", head, re.I)
    if m:
        f["ikz"] = m.group(1)
        f["customer_inn"] = m.group(1)[3:13]
        f["customer_kpp"] = m.group(1)[13:22]
        hints["customer_inn"] = "из ИКЗ (знаки 4–13)"
        f["procurement_law"] = "44-fz"

    # дата: «от 18 мая 2026» / «18.05.2026» в шапке до преамбулы; «__2026» — не заполнена.
    # Даты законов («от 05.04.2013 №44-ФЗ») отсекаются: за ними идёт «№».
    cut = re.search(r"именуем", head)
    top = head[: cut.start()] if cut else head[:700]
    m = re.search(r"«?(\d{1,2})»?\s*(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s*(\d{4})(?!\s*[№N])", top)
    if m:
        f["date"] = date_iso(m.group(0))
        hints["date"] = "шапка договора"
    else:
        m = re.search(r"(?<![\d.])(\d{2}\.\d{2}\.\d{4})(?![\d.])(?!\s*(?:г\.\s*)?[№N])", top)
        if m:
            f["date"] = date_iso(m.group(1))
            hints["date"] = "шапка договора"
    if not f.get("date") and re.search(r"_{2,}\s*20\d\d", top):
        f["date"] = None
        hints["date"] = "дата в тексте не заполнена (проект из ЕИС)"

    # цена
    m = re.search(r"Цена\s+(?:контракта|договора)\s+составляет\s*([\d\s ]+)\s*(?:руб\w*|\()\s*(?:\d{2})?\s*(?:коп\w*)?", t, re.I)
    m2 = re.search(r"Цена\s+(?:контракта|договора)\s+составляет\s*([\d\s ]+)\s*руб\w*\s*(\d{2})\s*коп", t, re.I)
    if m2:
        f["price_rub"] = num(m2.group(1) + "." + m2.group(2))
        hints["price_rub"] = "п. «Цена контракта»"
    elif m:
        f["price_rub"] = num(m.group(1))
        hints["price_rub"] = "п. «Цена контракта»"
    else:
        m = re.search(r"(?:стоимость|цена)\s+(?:работ|договора|контракта)[^\d\n]{0,80}?([\d\s ]{5,}[,.]\d{2})\s*(?:руб|₽)", t, re.I)
        if m:
            f["price_rub"] = num(m.group(1))
            hints["price_rub"] = "раздел о цене"
    if f.get("price_rub") is not None:
        seg = t[max(0, (m2 or m).start() - 50):(m2 or m).end() + 400] if (m2 or m) else ""
        if re.search(r"НДС\s+не\s+облага|без\s+НДС", seg, re.I):
            f["price_includes_vat"] = False
        elif re.search(r"с\s+учетом\s+(?:налога на добавленную стоимость|НДС)|включая\s+НДС|в том числе НДС", seg, re.I):
            f["price_includes_vat"] = True

    # НМЦК — только если рядом стоит сумма в рублях (а не «10 процентов НМЦК» из раздела о штрафах)
    m = re.search(r"начальн\w+\s+\(максимальн\w+\)\s+цен\w+[^\n\d]{0,40}?составля\w+\s*([\d\s ]+[,.]?\d{0,2})\s*руб", t, re.I)
    if m:
        f["nmck_rub"] = num(m.group(1))
        hints["nmck_rub"] = "упоминание начальной (максимальной) цены в договоре"

    # сроки
    m = re.search(r"начало\s+выполнения\s+работ:?\s*(?:с\s*)?(\d{2}\.\d{2}\.\d{4}|«?\d{1,2}»?\s*[а-я]+\s*\d{4})", t, re.I)
    if m:
        f["period_from"] = date_iso(m.group(1))
    m = re.search(r"окончание\s+выполнения\s+работ:?\s*(?:по\s*|до\s*)?(\d{2}\.\d{2}\.\d{4}|«?\d{1,2}»?\s*[а-я]+\s*\d{4})", t, re.I)
    if m:
        f["period_to"] = date_iso(m.group(1))

    # стороны
    pre = re.search(r"(?P<a>[^\n]{2,600}?),?\s*именуем\w*\s+в\s+дальнейшем\s*[–—-]?\s*«?(?P<ra>Заказчик|Генподрядчик|Генеральный подрядчик|Застройщик|Технический заказчик)»?.*?с\s+одной\s+стороны,?\s+и\s+(?P<b>[^\n]{5,400}?)(?:,\s*именуем\w*\s+в\s+дальнейшем\s*[–—-]?\s*«?(?P<rb>Подрядчик|Субподрядчик|Генподрядчик|Исполнитель)»?|\s+в\s+лице)", t, re.S)
    if pre:
        a = pre.group("a").split("\n")[-1]
        f["customer_name"] = short_name(re.sub(r"^\S*\s*20\d\d\s*", "", a).split(" в лице")[0])
        f["customer_role_word"] = pre.group("ra")
        f["contractor_name"] = short_name(pre.group("b").split(" в лице")[0].split(", именуем")[0])
        f["contractor_role_word"] = pre.group("rb") or "Подрядчик"
        hints["customer_name"] = "преамбула"
        hints["contractor_name"] = "преамбула"

    # протокол торгов и закон
    m = re.search(r"протокол\w*\s*№\s*([\d\-/A-Za-zА-Яа-я]+)\s*от\s*(\d{2}\.\d{2}\.\d{4})", t, re.I)
    if m:
        f["protocol"] = f"протокол № {m.group(1)} от {m.group(2)}"
    if re.search(r"44-ФЗ|О контрактной системе", t):
        f["procurement_law"] = "44-fz"
    elif re.search(r"223-ФЗ|о закупках товаров, работ, услуг отдельными видами юридических лиц", t, re.I):
        f["procurement_law"] = "223-fz"
    if f.get("procurement_law") in ("44-fz", "223-fz"):
        f["procurement"] = "competitive"
    elif re.search(r"по\s+(?:итогам|результатам)\s+(?:аукцион|конкурс|торг|закупк|тендер)", t, re.I):
        f["procurement"] = "competitive"
        f["procurement_law"] = "unknown"
    elif re.search(r"единственн\w+\s+поставщик|без\s+проведения\s+торгов", t, re.I):
        f["procurement"] = "direct"
    else:
        f["procurement"] = "unknown"
    hints["procurement"] = "; ".join(x for x in [f.get("protocol"), {"44-fz": "ссылки на 44-ФЗ", "223-fz": "ссылки на 223-ФЗ"}.get(f.get("procurement_law"), None),
                                                  ("ИКЗ " + f["ikz"]) if f.get("ikz") else None] if x)

    # предмет и объект
    m = re.search(r"1\.1\.\s*(.+?)(?:\n|$)", t)
    if m:
        f["subject_text"] = re.sub(r"\s+", " ", m.group(1)).strip()[:1200]
    m = re.search(r"Место\s+нахождения\s+объекта[^:\n]*:\s*(.+?)(?:\n|\*|$)", t, re.I) or re.search(r"(?:адрес\w*\s+объекта|место\s+выполнения\s+работ)[^:\n]*:\s*(.+?)(?:\n|$)", t, re.I)
    if m:
        f["object_address"] = re.sub(r"\s+", " ", m.group(1)).strip(" .*")
    m = re.search(r"Результатом\s+работ[^\n]*?являются\s+(.+?)(?:\n|$)", t, re.I)
    if m:
        f["result_text"] = re.sub(r"\s+", " ", m.group(1)).strip()

    # вид работ
    low = t.lower()
    if re.search(r"капитальн\w+\s+ремонт", low[:8000]):
        f["work_type"] = "capital_repair"
    elif re.search(r"текущ\w+\s+ремонт", low[:8000]):
        f["work_type"] = "current_repair"
    elif re.search(r"реконструкци", low[:4000]):
        f["work_type"] = "reconstruction"
    elif re.search(r"\bснос\w*\b|демонтаж\w*\s+здани", low[:4000]):
        f["work_type"] = "demolition"
    elif re.search(r"проектн\w+\s+документаци|разработк\w+\s+проект", low[:4000]):
        f["work_type"] = "design"
    elif re.search(r"инженерн\w+\s+изыскан", low[:4000]):
        f["work_type"] = "survey"
    elif re.search(r"строительств\w+\s+(?:объекта|здания|сооружения)", low[:4000]):
        f["work_type"] = "construction"
    elif re.search(r"\bремонт", low[:4000]):
        f["work_type"] = "repair_unspecified"
    else:
        f["work_type"] = "unknown"

    m = re.search(r"\((\d\d\.\d\d\.\d\d\.\d{3})\)", t)
    if m:
        f["okpd2"] = m.group(1)
    f["mentions_sro"] = bool(re.search(r"саморегулируем|\bСРО\b", t))
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
def customer_kind_guess(name: str | None) -> tuple[str, str]:
    n = (name or "").lower()
    if not n:
        return "unknown", ""
    if re.search(r"фонд\w*\s+капитальн\w+\s+ремонт|региональн\w+\s+оператор", n):
        return "regional_operator", "региональный оператор капитального ремонта — по наименованию"
    if re.search(r"специализированн\w+\s+застройщик|\bсз\b", n):
        return "developer", "специализированный застройщик — по наименованию; проверить разрешение на строительство"
    if re.search(r"техническ\w+\s+заказчик", n):
        return "technical_customer", "по наименованию; проверить договор с застройщиком"
    if re.search(r"учреждени|гбоу|гбдоу|гбу|мбоу|мбдоу|мку|мау|гку|гау|казенн|бюджетн|автономн|администраци|комитет|управлени|министерств|департамент", n):
        return "operator", "государственное/муниципальное учреждение или орган: здание закреплено на праве оперативного управления — лицо, ответственное за эксплуатацию (ч. 1 ст. 55.25 ГрК РФ); право по выписке ЕГРН не проверялось"
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
    ckind, ckind_basis = customer_kind_guess(f.get("customer_name"))
    wt = f.get("work_type", "unknown")
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
    if texts["contract"] and f.get("mentions_sro"):
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
