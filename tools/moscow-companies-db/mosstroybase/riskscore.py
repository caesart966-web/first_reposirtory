"""Эвристическая оценка риска «технической»/мёртвой компании.

Не заменяет юридическую проверку контрагента — отсеивает типовой мусор
(компании под угрозой исключения из ЕГРЮЛ, без единого контакта, с нулевой
живостью, парно зарегистрированные по одному адресу) перед выгрузкой лидов.
Признаки и веса подобраны вручную по разбору реальных дневных пачек.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

_FREE_EMAIL_DOMAINS = {
    "mail.ru", "yandex.ru", "gmail.com", "inbox.ru", "bk.ru",
    "list.ru", "rambler.ru", "yahoo.com", "ya.ru",
}
# Совпадение адреса + регистрация в пределах этого окна — признак пакетной
# (технической) регистрации нескольких юрлиц разом
_PAIRED_REG_WINDOW_DAYS = 14

# score >= JUNK_THRESHOLD — явный мусор; >= CHECK_THRESHOLD — под вопросом
JUNK_THRESHOLD = 5
CHECK_THRESHOLD = 2


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        return None


def _paired_inns(companies: list[dict]) -> set[str]:
    """ИНН компаний, зарегистрированных по тому же адресу, что и другая
    компания из выборки, в пределах ±14 дней."""
    by_address: dict[str, list[dict]] = {}
    for c in companies:
        addr = (c.get("address") or "").strip()
        if addr:
            by_address.setdefault(addr, []).append(c)
    paired: set[str] = set()
    for group in by_address.values():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            d1 = _parse_date(group[i].get("reg_date"))
            if d1 is None:
                continue
            for j in range(i + 1, len(group)):
                d2 = _parse_date(group[j].get("reg_date"))
                if d2 is not None and abs((d1 - d2).days) <= _PAIRED_REG_WINDOW_DAYS:
                    paired.add(group[i]["inn"])
                    paired.add(group[j]["inn"])
    return paired


def score_company(company: dict, paired_inns: set[str] = frozenset()) -> tuple[int, list[str]]:
    """Возвращает (score, причины) для одной компании.

    paired_inns — результат _paired_inns()/score_all() по всей выборке;
    без него признак парной регистрации просто не проверяется.
    """
    score = 0
    reasons: list[str] = []

    status = (company.get("egrul_status") or "").strip()
    lowered = status.lower()
    if "недостоверн" in lowered or "исключени" in lowered:
        score += 5
        reasons.append("ФНС: решение об исключении/недостоверность")
    elif lowered == "не действует":
        score += 5
        reasons.append("не действует")
    elif not status:
        score += 1
        reasons.append("статус не проверен ЕГРЮЛ")

    phones = list(company.get("phones") or []) + list(company.get("phones_site") or [])
    emails = list(company.get("emails") or [])
    has_site = bool((company.get("website") or "").strip())

    if not phones and not emails:
        score += 3
        reasons.append("нет контактов вообще")
    elif (not has_site and emails
          and all(e.split("@")[-1].lower() in _FREE_EMAIL_DOMAINS for e in emails)
          and len(set(phones)) <= 1):
        score += 1
        reasons.append("только бесплатная почта и/или 1 номер, нет сайта")

    employees = company.get("employees")
    taxes = company.get("taxes_paid")
    if employees == 0 and not taxes:
        score += 2
        reasons.append("0 сотрудников и 0 налогов")
    elif employees is None:
        reasons.append("признаки живости не запрошены")

    if company.get("inn") in paired_inns:
        score += 3
        reasons.append("парная регистрация: тот же адрес и дата рег. ±14 дней "
                        "с другой компанией из выборки")

    return score, reasons


def score_all(companies: Iterable[dict]) -> dict[str, tuple[int, list[str]]]:
    """Скор для каждой компании в выборке разом (нужен полный список — парная
    регистрация определяется сравнением компаний друг с другом)."""
    companies = list(companies)
    paired = _paired_inns(companies)
    return {c["inn"]: score_company(c, paired) for c in companies}


def is_risky(score: int) -> bool:
    """Порог, который используют export/daily при --exclude-risky."""
    return score >= CHECK_THRESHOLD
