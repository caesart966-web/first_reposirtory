"""Слияние находок в атрибуты и расчёт уверенности.

Модель уверенности — «шумное ИЛИ» по независимым источникам:
    P = 1 - Π(1 - c_i)
Два независимых источника с уверенностью 0.6 дают 0.84 — это и есть смысл
кросс-проверки. Повторы внутри одного источника (та же почта на пяти страницах
сайта) дают лишь небольшую надбавку, а не умножаются как независимые.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .models import Attribute, Finding, Provenance, Query
from .normalize import (
    email_domain, is_role_email, name_key, registrable_domain, same_site,
)

# Бесплатные почтовые провайдеры: адрес на них не подтверждает связь с доменом.
FREEMAIL = {
    "mail.ru", "inbox.ru", "list.ru", "bk.ru", "internet.ru", "yandex.ru",
    "ya.ru", "yandex.com", "gmail.com", "googlemail.com", "rambler.ru",
    "outlook.com", "hotmail.com", "live.com", "icloud.com", "me.com",
    "proton.me", "protonmail.com", "vk.com", "bezh.ru", "narod.ru",
}

REPEAT_BONUS = 0.02      # надбавка за каждое дополнительное упоминание в том же источнике
REPEAT_BONUS_CAP = 0.10


def _dedup_key(kind: str, value: str) -> str:
    if kind == "name":
        return name_key(value)
    if kind in ("email", "domain", "social", "url"):
        return value.lower().rstrip("/")
    if kind == "person":
        return " ".join(value.lower().split())
    if kind == "address":
        return "".join(ch for ch in value.lower() if ch.isalnum())
    return value


def noisy_or(confidences: Iterable[float]) -> float:
    product = 1.0
    for c in confidences:
        product *= (1.0 - max(0.0, min(1.0, c)))
    return 1.0 - product


def merge_findings(findings: Iterable[Finding]) -> dict[str, list[Attribute]]:
    """Группирует находки по (вид, нормализованное значение) и считает уверенность."""
    groups: dict[tuple[str, str], list[Finding]] = defaultdict(list)
    for f in findings:
        groups[(f.kind, _dedup_key(f.kind, f.value))].append(f)

    result: dict[str, list[Attribute]] = defaultdict(list)
    for (kind, _), items in groups.items():
        by_source: dict[str, list[Finding]] = defaultdict(list)
        for f in items:
            by_source[f.provenance.source].append(f)

        per_source_conf: list[float] = []
        for source_items in by_source.values():
            best = max(f.confidence for f in source_items)
            bonus = min((len(source_items) - 1) * REPEAT_BONUS, REPEAT_BONUS_CAP)
            per_source_conf.append(min(1.0, best + bonus))

        # Потолок 0.99: абсолютной уверенности по открытым источникам не бывает.
        confidence = min(0.99, noisy_or(per_source_conf))
        # Каноничное значение — из находки с максимальной уверенностью.
        best_finding = max(items, key=lambda f: f.confidence)
        extra: dict = {}
        for f in items:
            for k, v in f.extra.items():
                if k not in extra and v not in (None, "", [], {}):
                    extra[k] = v
        # Если у значения есть хотя бы одно неспекулятивное подтверждение,
        # метка «гипотеза» снимается: догадка подтвердилась и стала фактом.
        if extra.get("hypothesis") and any(not f.extra.get("hypothesis") for f in items):
            extra.pop("hypothesis")
            extra["guess_confirmed"] = True

        sources: list[Provenance] = []
        seen_prov: set[tuple] = set()
        for f in sorted(items, key=lambda f: -f.confidence):
            key = (f.provenance.source, f.provenance.url, f.provenance.note)
            if key in seen_prov:
                continue
            seen_prov.add(key)
            sources.append(f.provenance)
        result[kind].append(Attribute(kind, best_finding.value, confidence, sources, extra))

    for kind, items in result.items():
        items.sort(key=lambda a: (-a.confidence, a.value))
    return dict(result)


def apply_relevance(attributes: dict[str, list[Attribute]], query: Query) -> list[str]:
    """Корректирует уверенность по связи с компанией. Возвращает пояснения-предупреждения."""
    notes: list[str] = []

    # Основной домен: из запроса либо самый уверенный найденный.
    main_domain = query.domain
    if not main_domain and attributes.get("domain"):
        main_domain = attributes["domain"][0].value
    main_reg = registrable_domain(main_domain) if main_domain else None

    for email in attributes.get("email", []):
        domain = email_domain(email.value)
        email.extra.setdefault("role_account", is_role_email(email.value))
        if domain in FREEMAIL:
            email.extra["mail_provider"] = "freemail"
            email.confidence *= 0.85
        elif main_reg and registrable_domain(domain) == main_reg:
            email.extra["corporate"] = True
            email.confidence = min(0.99, email.confidence * 1.15 + 0.05)
        elif main_reg:
            # Почта на чужом домене — вероятно, подрядчик/агрегатор/разработчик сайта.
            email.extra["foreign_domain"] = True
            email.confidence *= 0.55
            notes.append(
                f"почта {email.value} на стороннем домене {domain} — проверьте связь с компанией"
            )

    for domain in attributes.get("domain", []):
        if main_reg and not same_site(domain.value, main_reg):
            domain.confidence *= 0.8

    for kind in attributes:
        attributes[kind].sort(key=lambda a: (-a.confidence, a.value))
    return notes


def drop_below(attributes: dict[str, list[Attribute]], threshold: float) -> dict[str, list[Attribute]]:
    return {k: [a for a in v if a.confidence >= threshold] for k, v in attributes.items()}
