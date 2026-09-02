"""Отчёты по снятому снапшоту. Только чтение БД, ничего не пишет.

Главный вопрос перед первым живым прогоном: API реестра отдаёт всех членов, включая
исключённых, или только срез действующих. Во втором случае backfill не поедет в
принципе, и это надо увидеть сразу, а не гадать по нулю сигналов.
"""
from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Any, Optional

from collectors.base import EXCLUDED_CLS, SUSPENDED_CLS, classify_status
from .db import Database
from .export import select_leads
from .models import SIGNAL_TITLES, RegistryRow
from .scoring import score_org
from .utils import normalize_inn, today_str

WINDOWS = (30, 90, 180)

log = logging.getLogger("sro_leads")


def _dates(values: list[Optional[str]]) -> tuple[int, Optional[str], Optional[str]]:
    filled = sorted(v for v in values if v)
    return len(filled), (filled[0] if filled else None), (filled[-1] if filled else None)


def _status_titles(cfg: dict[str, Any], source: str) -> dict[str, str]:
    rcfg = cfg.get("registry", {})
    titles = dict(rcfg.get("status_code_titles") or {})
    titles.update((rcfg.get(source) or {}).get("status_code_titles") or {})
    return {str(k): str(v) for k, v in titles.items()}


def snapshot_report(db: Database, cfg: dict[str, Any], source: str,
                    snapshot_date: Optional[str] = None) -> tuple[bool, str]:
    """(backfill применим?, текст отчёта) по снапшоту источника за дату.

    Окна 30/90/180 дней отсчитываются от даты снапшота: это ровно то, что дал бы
    `--backfill N`, запущенный в день снятия снапшота.
    """
    dates = db.snapshot_dates(source)
    if not dates:
        return False, f"Снапшотов источника «{source}» в базе нет. Снимите: python run.py --only {source}_registry"
    snapshot_date = snapshot_date or dates[0]
    if snapshot_date not in dates:
        return False, (f"Снапшота {source} за {snapshot_date} нет.\n"
                       f"Есть даты: {', '.join(dates[:10])}")

    rows: list[RegistryRow] = db.snapshot_rows(source, snapshot_date)
    meta = db.snapshot_meta(source, snapshot_date)
    classes = cfg.get("registry", {}).get("status_classes", {})
    titles = _status_titles(cfg, source)
    total = len(rows)
    lines: list[str] = []
    add = lines.append

    add(f"== Снапшот {source} за {snapshot_date}")
    add(f"   записей: {total}, организаций (уникальных ИНН): {len({r.inn for r in rows})}")
    if meta:
        add(f"   полнота: {meta.describe()}")
        if meta.is_partial:
            add(f"   ВНИМАНИЕ: снапшот частичный, цифры ниже неполные. "
                f"Снять заново: python run.py --drop-snapshot {source} --date {snapshot_date}")
    else:
        add("   полнота: метаданных нет (снапшот снят до появления snapshot_meta)")

    # 2. Распределение по коду статуса
    codes = Counter((r.status_code or "—") for r in rows)
    texts: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        texts[r.status_code or "—"][r.status or "—"] += 1
    add("")
    add("== Распределение по status_code:")
    add(f"   {'код':<16} {'расшифровка':<44} {'записей':>8} {'доля':>7}  класс")
    for code, cnt in codes.most_common():
        text = texts[code].most_common(1)[0][0]
        title = titles.get(code) or text
        cls = classify_status(text, classes)
        add(f"   {code:<16} {title[:44]:<44} {cnt:>8} {cnt / total:>6.1%}  {cls}")
    lead_rows = [r for r in rows if classify_status(r.status, classes) in (EXCLUDED_CLS, SUSPENDED_CLS)]
    add(f"   из них лидовых (исключены или приостановлены): {len(lead_rows)}")

    # 3. Даты статуса
    n_status, min_status, max_status = _dates([r.status_date for r in rows])
    add("")
    add("== Дата статуса (status_date):")
    add(f"   заполнена у {n_status} из {total} ({n_status / total if total else 0:.1%}), "
        f"min {min_status or '—'}, max {max_status or '—'}")

    # 4. Окна
    anchor = date.fromisoformat(snapshot_date)
    add("")
    add("== Записи в окне (от даты снапшота):")
    add(f"   {'окно':<10} {'всего с датой':>14} {'из них лидовых':>16}")
    in_window: dict[int, int] = {}
    for days in WINDOWS:
        start = (anchor - timedelta(days=days)).isoformat()
        all_n = sum(1 for r in rows if r.status_date and start <= r.status_date <= snapshot_date)
        lead_n = sum(1 for r in lead_rows if r.status_date and start <= r.status_date <= snapshot_date)
        in_window[days] = lead_n
        add(f"   {str(days) + ' дней':<10} {all_n:>14} {lead_n:>16}")

    # 5. Дата регистрации
    n_reg, min_reg, max_reg = _dates([r.reg_date for r in rows])
    add("")
    add("== Дата регистрации в реестре (reg_date):")
    add(f"   заполнена у {n_reg} из {total} ({n_reg / total if total else 0:.1%}), "
        f"min {min_reg or '—'}, max {max_reg or '—'}")

    # Вердикт
    single_status = len(codes) <= 1
    no_dates = n_status == 0
    add("")
    if single_status or no_dates:
        why = []
        if single_status:
            why.append(f"статус один на весь снапшот ({next(iter(codes))})")
        if no_dates:
            why.append("status_date пуста у всех записей")
        add(f"ВЕРДИКТ: API отдаёт срез действующих членов ({'; '.join(why)}), "
            f"backfill невозможен, работаем через дифф")
        add(f"   Снимите обычный снапшот (python run.py --only {source}_registry) и ждите сутки до первого диффа.")
        return False, "\n".join(lines)
    add(f"ВЕРДИКТ: backfill применим, в окне 90 дней {in_window[90]} записей")
    add(f"   Запуск: python run.py --only {source}_registry --backfill 90")
    return True, "\n".join(lines)


# ---------------------------------------------------------------------------
# Ручная сверка лидов: карточка организации со всем, что о ней известно
# ---------------------------------------------------------------------------
def card_url(cfg: dict[str, Any], source: str, inn: str, reg_number: Optional[str]) -> Optional[str]:
    """Ссылка на карточку в реестре по шаблону registry.<источник>.card_url_template."""
    tpl = ((cfg.get("registry", {}).get(source) or {}).get("card_url_template") or "").strip()
    if not tpl:
        return None
    try:
        return tpl.format(inn=inn, reg_number=reg_number or "")
    except (KeyError, IndexError):
        return None


def _pretty_json(raw: Optional[str], indent: str = "      ") -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except ValueError:
        return [indent + raw[:500]]
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
    return [indent + line for line in text.splitlines()]


def inspect_orgs(db: Database, cfg: dict[str, Any], inns: list[str],
                 date: Optional[str] = None) -> str:
    """Карточки организаций для ручной сверки с реестром. Только чтение БД."""
    date = date or today_str()
    scfg = cfg.get("scoring", {})
    signals_by_inn = db.signals_by_inn(inns)
    outreach = db.outreach_map()
    lines: list[str] = []
    add = lines.append

    for i, raw_inn in enumerate(inns, 1):
        inn = normalize_inn(raw_inn) or raw_inn
        org = db.get_org(inn)
        sigs = signals_by_inn.get(inn, [])
        res = score_org(inn, sigs, scfg, date)
        if i > 1:
            add("")
        add("=" * 78)
        if org is None and not sigs:
            add(f"{inn}: в базе нет ни организации, ни сигналов")
            continue
        add(f"{inn}  {org.name if org and org.name else '(название неизвестно)'}")
        add(f"   регион: {(org.region if org else None) or '—'}   ОКВЭД: {(org.okved if org else None) or '—'}   "
            f"ОГРН: {(org.ogrn if org else None) or '—'}")
        add(f"   скор: {res.score}   приоритет: {res.priority}   "
            f"статус ЕГРЮЛ: {(org.status if org else None) or '—'}   "
            f"обзвон: {outreach[inn]['status'] if inn in outreach else 'new'}")
        if res.date_conflict:
            add("   ФЛАГ date_conflict: есть вступление в СРО, но даты сравнить нельзя — проверьте вручную")
        if res.suppressed:
            add(f"   погашенные сигналы (вступил позже): {', '.join(sorted(set(res.suppressed)))}")

        add("")
        add(f"   Сигналы ({len(sigs)}):")
        if not sigs:
            add("      нет")
        for s in sigs:
            counted = "учтён" if s["signal_type"] in res.types else "не учтён в скоре"
            add(f"      {SIGNAL_TITLES.get(s['signal_type'], s['signal_type'])} "
                f"[{s['signal_type']}] {s['signal_date']}  источник {s['source']}  "
                f"обнаружен {s['detected_by'] or '—'}  ({counted})")
            if s["url"]:
                add(f"         ссылка из сигнала: {s['url']}")
            add("         raw_json:")
            lines.extend(_pretty_json(s["raw_json"], "            "))

        snap_rows = db.snapshot_rows_for_inn(inn)
        add("")
        add(f"   Записи в снапшотах реестра ({len(snap_rows)}):")
        if not snap_rows:
            add("      нет — организация в снапшотах не найдена (лид из тендеров или снапшот не снят)")
        for r in snap_rows:
            add(f"      {r['source']} за {r['snapshot_date']}: {r['sro_name']}, рег.№ {r['reg_number'] or '—'}, "
                f"статус «{r['status'] or '—'}» (код {r['status_code'] or '—'}), "
                f"дата статуса {r['status_date'] or '—'}, дата регистрации {r['reg_date'] or '—'}")
            if r["url"]:
                add(f"         карточка члена: {r['url']}")

        add("")
        add("   Ссылки для сверки глазами:")
        seen_sources = {r["source"] for r in snap_rows} or {s["source"] for s in sigs if s["source"] in ("nostroy", "nopriz")}
        reg_number = next((r["reg_number"] for r in snap_rows if r["reg_number"]), None)
        for source in sorted(seen_sources or {"nostroy", "nopriz"}):
            url = card_url(cfg, source, inn, reg_number)
            if url:
                add(f"      {source}: {url}")

        add("")
        add("   Контакты:")
        if org is None:
            add("      организация не обогащена")
        else:
            add(f"      сайт: {org.site or '—'}  (проверка: {org.site_verified or '—'})")
            add(f"      телефон: {org.phone or '—'}   почта: {org.email or '—'}")
            if org.phone_unverified or org.email_unverified:
                add(f"      с неподтверждённого сайта — телефон: {org.phone_unverified or '—'}, "
                    f"почта: {org.email_unverified or '—'}")
            add(f"      руководитель: {org.director or '—'}   обогащено: {org.enriched_at or 'нет'}")
    return "\n".join(lines)


def top_inns(db: Database, cfg: dict[str, Any], n: int, date: Optional[str] = None) -> list[str]:
    """N организаций с верха листа «Горячие» по тем же фильтрам, что и экспорт.

    Если горячих нет, берём верх листа «Все лиды» — иначе команда молча ничего не покажет.
    """
    leads, _ = select_leads(db, cfg, date or today_str())
    hot = [l for l in leads if l["priority"] == 1 and l["status"] == "new"]
    if not hot and leads:
        log.info("--inspect-top: лидов приоритета 1 нет, берём верх листа «Все лиды»")
    return [l["inn"] for l in (hot or leads)[:n]]
