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
    компания из выборки, в пределах ±14 дней.

    Внутри каждого адреса сравниваем не все пары (O(k²) — на массовых
    адресах регистрации с тысячами компаний это considerably минуты), а
    только соседей по дате после сортировки: если у компании X есть хоть
    один сосед по адресу в пределах 14 дней, он гарантированно окажется
    среди двух ближайших по дате соседей в отсортированном списке —
    O(k log k) на группу вместо O(k²).
    """
    by_address: dict[str, list[dict]] = {}
    for c in companies:
        addr = (c.get("address") or "").strip()
        if addr:
            by_address.setdefault(addr, []).append(c)
    paired: set[str] = set()
    for group in by_address.values():
        if len(group) < 2:
            continue
        dated = sorted(
            (
                (d, c["inn"]) for c in group
                if (d := _parse_date(c.get("reg_date"))) is not None
            ),
            key=lambda pair: pair[0],
        )
        for i in range(len(dated) - 1):
            d1, inn1 = dated[i]
            d2, inn2 = dated[i + 1]
            if (d2 - d1).days <= _PAIRED_REG_WINDOW_DAYS:
                paired.add(inn1)
                paired.add(inn2)
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
        # Отсутствие статуса — не признак риска, а просто нехватка данных
        # (компания ещё не дообогащена). Не штрафуем, только отмечаем.
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
