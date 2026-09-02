"""Отчёты по снятому снапшоту. Только чтение БД, ничего не пишет.

Главный вопрос перед первым живым прогоном: API реестра отдаёт всех членов, включая
исключённых, или только срез действующих. Во втором случае backfill не поедет в
принципе, и это надо увидеть сразу, а не гадать по нулю сигналов.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Any, Optional

from collectors.base import EXCLUDED_CLS, SUSPENDED_CLS, classify_status
from .db import Database
from .models import RegistryRow

WINDOWS = (30, 90, 180)


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
