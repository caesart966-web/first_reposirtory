"""Кросс-сверка и скоринг достоверности контактов (0–100).

Веса (настраиваются в config.yaml, секция scoring — значения по ТЗ, п. 6):
  +40 источник уровня A (официальный реестр);
  +30 контакт найден на домене, подтверждённом по ИНН;
  +15 контакт встретился в 2+ независимых источниках;
  +10 корпоративный домен почты совпадает с сайтом компании;
  -20 источник уровня D без верификации;
  -30 компания в статусе «ликвидировано».

Кросс-сверка: одинаковый контакт из разных источников объединяется в один
MergedContact со списком происхождений — не дублируется, а скоринг растёт.
"""
from __future__ import annotations

from typing import Optional

from core.config import Config
from core.models import (
    Company,
    Contact,
    ContactOrigin,
    ContactType,
    MergedContact,
    SourceLevel,
)
from validators.email import domain_of
from validators.phone import phone_type


def _merge_key(contact: Contact) -> tuple[str, str]:
    value = contact.value.strip().lower()
    return (contact.type.value, value)


def merge_contacts(contacts: list[Contact]) -> list[MergedContact]:
    """Объединить дубликаты одного контакта из разных источников."""
    merged: dict[tuple[str, str], MergedContact] = {}
    for contact in contacts:
        key = _merge_key(contact)
        origin = ContactOrigin(
            source=contact.source,
            source_url=contact.source_url,
            level=contact.level,
            collected_at=contact.collected_at,
        )
        if key not in merged:
            merged[key] = MergedContact(
                type=contact.type,
                value=contact.value.strip(),
                raw=contact.raw or contact.value,
                origins=[origin],
                extra=dict(contact.extra),
            )
        else:
            entry = merged[key]
            if not any(o.source == origin.source and o.source_url == origin.source_url
                       for o in entry.origins):
                entry.origins.append(origin)
            # extra объединяем, не затирая уже известное
            for k, v in contact.extra.items():
                entry.extra.setdefault(k, v)
    return list(merged.values())


def score_contact(merged: MergedContact, company: Company, cfg: Config) -> int:
    """Посчитать достоверность одного объединённого контакта."""
    w = cfg.get("scoring", {})
    score = 0
    levels = {o.level for o in merged.origins}
    site_domain = domain_of(company.website or "") if company.website else None

    if SourceLevel.A in levels:
        score += int(w.get("level_a", 40))
    elif SourceLevel.C in levels:
        score += int(w.get("base_c", 20))

    from_site = any(o.level == SourceLevel.B for o in merged.origins)
    if from_site:
        if company.website_verified and merged.extra.get("site_verified_by_inn", True):
            score += int(w.get("verified_site", 30))
        else:
            score += int(w.get("base_b_unverified", 15))

    if len(merged.sources) >= 2:
        score += int(w.get("multi_source", 15))

    if merged.type == ContactType.EMAIL and site_domain:
        email_domain = domain_of(merged.value)
        if email_domain == site_domain or email_domain.endswith("." + site_domain):
            score += int(w.get("corp_domain", 10))

    only_d = levels == {SourceLevel.D}
    site_unverified = from_site and not company.website_verified
    if only_d or (site_unverified and levels <= {SourceLevel.B, SourceLevel.D}
                  and SourceLevel.A not in levels and SourceLevel.C not in levels
                  and len(merged.sources) < 2):
        # уровень D (или сайт-кандидат без верификации) без независимого подтверждения
        if only_d:
            score += int(w.get("level_d_unverified", -20))

    if (company.entity_status or "").lower().startswith("ликвид"):
        score += int(w.get("liquidated", -30))

    return max(0, min(100, score))


def _pick_primary_email(emails: list[MergedContact], company: Company) -> Optional[MergedContact]:
    if not emails:
        return None
    site_domain = domain_of(company.website or "") if company.website else None

    def rank(m: MergedContact) -> tuple:
        domain = domain_of(m.value)
        corporate = 1 if site_domain and (
            domain == site_domain or domain.endswith("." + site_domain)) else 0
        return (m.confidence, corporate, len(m.sources), -len(m.value))

    return max(emails, key=rank)


def _pick_primary_phone(phones: list[MergedContact]) -> Optional[MergedContact]:
    if not phones:
        return None

    def rank(m: MergedContact) -> tuple:
        # при равной достоверности основной — городской/8-800 (номер офиса)
        kind = phone_type(m.value)
        kind_rank = {"городской": 2, "8-800": 2, "мобильный": 1}.get(kind, 0)
        return (m.confidence, kind_rank, len(m.sources))

    return max(phones, key=rank)


def merge_and_score(company: Company, contacts: list[Contact],
                    cfg: Config) -> list[MergedContact]:
    """Полный цикл: объединение, скоринг, выбор основных контактов."""
    merged = merge_contacts(contacts)
    for m in merged:
        m.confidence = score_contact(m, company, cfg)

    emails = [m for m in merged if m.type == ContactType.EMAIL]
    phones = [m for m in merged if m.type == ContactType.PHONE]
    primary_email = _pick_primary_email(emails, company)
    primary_phone = _pick_primary_phone(phones)
    if primary_email:
        primary_email.is_primary = True
    if primary_phone:
        primary_phone.is_primary = True

    merged.sort(key=lambda m: (m.type.value, -m.confidence, m.value))
    return merged
