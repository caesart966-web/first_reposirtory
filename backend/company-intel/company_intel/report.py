"""Отчёт: Markdown для человека, JSON и CSV для машин.

Отчёт устроен так, чтобы каждое значение можно было перепроверить: рядом с
телефоном и почтой стоят уверенность и ссылка на страницу, откуда они взяты.
Гипотезы (например, адреса по шаблону) вынесены в отдельный раздел и никогда
не смешиваются с подтверждёнными данными.
"""
from __future__ import annotations

import csv
import io

from .models import Attribute, Profile
from .normalize import format_phone_ru

KIND_TITLES = {
    "name": "Наименования",
    "inn": "ИНН", "ogrn": "ОГРН", "kpp": "КПП", "okpo": "ОКПО",
    "domain": "Домены и поддомены",
    "email": "Электронная почта",
    "phone": "Телефоны",
    "address": "Адреса",
    "person": "Люди",
    "social": "Соцсети и мессенджеры",
    "url": "Упоминания в интернете",
    "fact": "Прочие сведения",
}
ORDER = ("name", "inn", "ogrn", "kpp", "okpo", "address", "phone", "email",
         "person", "domain", "social", "fact", "url")


HYPOTHESIS_FLOOR = 0.1   # гипотезы намеренно имеют низкую уверенность


def _keep(attr: Attribute, min_confidence: float) -> bool:
    """Гипотезы не отсекаются общим порогом — у них отдельный, более низкий."""
    floor = HYPOTHESIS_FLOOR if attr.extra.get("hypothesis") else min_confidence
    return attr.confidence >= floor


def confidence_badge(value: float) -> str:
    if value >= 0.8:
        return "высокая"
    if value >= 0.55:
        return "средняя"
    if value >= 0.3:
        return "низкая"
    return "гипотеза"


def _format_value(kind: str, attr: Attribute) -> str:
    if kind == "phone":
        text = format_phone_ru(attr.value)
        ext = attr.extra.get("extension")
        label = attr.extra.get("label")
        if ext:
            text += f" доб. {ext}"
        if label:
            text += f" ({label})"
        return text
    if kind == "person":
        position = attr.extra.get("position") or attr.extra.get("role")
        return f"{attr.value} — {position}" if position else attr.value
    if kind == "email" and attr.extra.get("role_account"):
        return f"{attr.value} (общий ящик)"
    return attr.value


def _sources_line(attr: Attribute, limit: int = 3) -> str:
    parts: list[str] = []
    for prov in attr.sources[:limit]:
        label = prov.source
        if prov.url:
            label = f"[{prov.source}]({prov.url})"
        if prov.note:
            label += f" — {prov.note}"
        parts.append(label)
    if len(attr.sources) > limit:
        parts.append(f"…ещё {len(attr.sources) - limit}")
    return "; ".join(parts)


def to_markdown(profile: Profile, min_confidence: float = 0.25) -> str:
    q = profile.query
    title = q.name or q.domain or q.inn or "компания"
    lines = [f"# Профиль: {title}", ""]

    asked = [f"{k}={v}" for k, v in (
        ("название", q.name), ("ИНН", q.inn), ("ОГРН", q.ogrn), ("домен", q.domain),
        ("почта", q.email), ("телефон", q.phone), ("человек", q.person),
        ("город", q.city)) if v]
    lines.append(f"**Исходные данные:** {', '.join(asked) or '—'}")
    stats = profile.stats
    lines.append(
        f"**Сбор:** {profile.started_at} → {profile.finished_at}, "
        f"находок {stats.get('findings', 0)}, "
        f"HTTP-запросов {stats.get('http', {}).get('requests', 0)} "
        f"(из кэша {stats.get('http', {}).get('cached', 0)}), "
        f"раундов {stats.get('rounds', 0)}"
    )
    lines.append("")

    hypotheses: list[tuple[str, Attribute]] = []
    for kind in ORDER:
        items = [a for a in profile.get(kind) if _keep(a, min_confidence)]
        real = []
        for attr in items:
            (hypotheses if attr.extra.get("hypothesis") else real).append((kind, attr))
        if not real:
            continue
        lines.append(f"## {KIND_TITLES.get(kind, kind)}")
        lines.append("")
        lines.append("| Значение | Уверенность | Источники |")
        lines.append("|---|---|---|")
        for _, attr in real:
            lines.append(
                f"| {_format_value(kind, attr)} | {attr.confidence:.2f} "
                f"({confidence_badge(attr.confidence)}) | {_sources_line(attr)} |"
            )
        lines.append("")

    if hypotheses:
        lines.append("## Гипотезы (не подтверждены)")
        lines.append("")
        lines.append("| Значение | Уверенность | Основание |")
        lines.append("|---|---|---|")
        for kind, attr in hypotheses:
            basis = "; ".join(p.note or p.source for p in attr.sources[:2])
            lines.append(f"| {_format_value(kind, attr)} | {attr.confidence:.2f} | {basis} |")
        lines.append("")

    if profile.warnings:
        lines.append("## Замечания")
        lines.append("")
        for warning in profile.warnings:
            lines.append(f"- {warning}")
        lines.append("")

    by_source = stats.get("by_source") or {}
    if by_source:
        lines.append("## Вклад источников")
        lines.append("")
        for name, count in sorted(by_source.items(), key=lambda x: -x[1]):
            lines.append(f"- `{name}`: находок {count}")
        lines.append("")

    lines.append("---")
    lines.append(
        "_Собрано из открытых источников. Перед использованием контактов "
        "в рассылке проверьте основание обработки данных (ст. 6 152-ФЗ) и "
        "требования ст. 18 «О рекламе»._"
    )
    return "\n".join(lines)


def to_csv(profile: Profile, min_confidence: float = 0.25) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["kind", "value", "confidence", "hypothesis", "sources", "extra"])
    for kind in ORDER:
        for attr in profile.get(kind):
            if not _keep(attr, min_confidence):
                continue
            writer.writerow([
                kind, attr.value, f"{attr.confidence:.3f}",
                "1" if attr.extra.get("hypothesis") else "0",
                " | ".join(f"{p.source}:{p.url or ''}" for p in attr.sources[:5]),
                "; ".join(f"{k}={v}" for k, v in attr.extra.items() if k != "hypothesis"),
            ])
    return buffer.getvalue()


def to_text(profile: Profile, min_confidence: float = 0.25) -> str:
    """Короткая сводка для терминала."""
    lines = []
    for kind in ORDER:
        items = [a for a in profile.get(kind) if _keep(a, min_confidence)]
        if not items:
            continue
        lines.append(f"{KIND_TITLES.get(kind, kind)}:")
        for attr in items[:10]:
            mark = "?" if attr.extra.get("hypothesis") else " "
            lines.append(
                f"  {mark} {_format_value(kind, attr):<48} {attr.confidence:.2f}  "
                f"[{', '.join(attr.source_names)}]"
            )
        if len(items) > 10:
            lines.append(f"    …ещё {len(items) - 10}")
        lines.append("")
    return "\n".join(lines)
