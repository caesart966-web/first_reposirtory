"""TenderGuru: участники/победители закупок, требующих СРО, которых нет в реестрах.

Читает все .xlsx из data/tenderguru/, достаёт ИНН заказчика и подрядчика, сумму, ОКПД, дату;
отбрасывает ИНН, которые есть в свежем снапшоте реестра (проектирование -> НОПРИЗ,
стройка -> НОСТРОЙ); остальным ставит сигнал. Обработанные файлы уезжают в processed/
после того, как оркестратор записал сигналы в БД.
"""
from __future__ import annotations

import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from core.models import (
    TENDER_NO_SRO_BUILD_HIGH,
    TENDER_NO_SRO_BUILD_MID,
    TENDER_NO_SRO_DESIGN,
    Signal,
)
from core.utils import clean_str, normalize_inn, parse_date, resolve_path, today_str

from .base import ACTIVE, SUSPENDED_CLS, Collector, org_states

log = logging.getLogger("sro_leads")

ROLE_SOURCE = {TENDER_NO_SRO_DESIGN: "nopriz", TENDER_NO_SRO_BUILD_HIGH: "nostroy", TENDER_NO_SRO_BUILD_MID: "nostroy"}


def parse_money(value: Any) -> Optional[float]:
    """«12 345 678,90 руб.» -> 12345678.9; «1,234,567.00» -> 1234567.0; мусор -> None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return None if value != value else float(value)  # NaN -> None
    s = str(value).replace("\xa0", "").replace(" ", "")
    s = re.sub(r"[^\d,.\-]", "", s).strip(",.")
    if not s:
        return None
    if "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        other = "." if dec == "," else ","
        s = s.replace(other, "").replace(dec, ".")
    elif "," in s or "." in s:
        sep = "," if "," in s else "."
        head, _, tail = s.rpartition(sep)
        if s.count(sep) == 1 and len(tail) in (1, 2):
            s = head + "." + tail          # десятичный разделитель
        else:
            s = s.replace(sep, "")         # разделитель тысяч
    try:
        return float(s)
    except ValueError:
        return None


def detect_columns(header: list[Any], spec: dict[str, list[str]]) -> dict[str, int]:
    """Логическое имя колонки -> индекс в строке. Подстроки из конфига, без учёта регистра."""
    names = [str(h).strip().lower() if h is not None else "" for h in header]
    mapping: dict[str, int] = {}
    for logical, keys in spec.items():
        wants_inn = logical.endswith("_inn")
        for key in keys:
            k = key.lower()
            for idx, h in enumerate(names):
                if not h or idx in mapping.values():
                    continue
                if k in h and (wants_inn or "инн" not in h):
                    mapping[logical] = idx
                    break
            if logical in mapping:
                break
    return mapping


def find_header_row(df: pd.DataFrame, spec: dict[str, list[str]], scan: int = 15) -> Optional[int]:
    """Заголовок не всегда в первой строке: ищем строку, где узнаётся хотя бы ИНН и ещё что-то."""
    best: Optional[tuple[int, int]] = None
    for i in range(min(scan, len(df))):
        mapping = detect_columns(list(df.iloc[i]), spec)
        has_inn = any(k.endswith("_inn") for k in mapping)
        if has_inn and len(mapping) >= 2:
            if best is None or len(mapping) > best[1]:
                best = (i, len(mapping))
    return best[0] if best else None


class TenderMatch(Collector):
    name = "tender_match"

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._done_files: list[Path] = []

    @property
    def tcfg(self) -> dict[str, Any]:
        return self.config.get("tenderguru", {})

    # ------------------------------------------------------------ реестры
    def registry_members(self) -> dict[str, Optional[set[str]]]:
        """Источник -> множество ИНН действующих/приостановленных членов по свежему снапшоту.
        None — снапшота по источнику нет."""
        classes = self.config.get("registry", {}).get("status_classes", {})
        out: dict[str, Optional[set[str]]] = {}
        for source in ("nostroy", "nopriz"):
            d = self.db.latest_snapshot_date(source)
            if not d:
                out[source] = None
                continue
            states = org_states(self.db.snapshot_rows(source, d), classes)
            out[source] = {inn for inn, (cls, _) in states.items() if cls in (ACTIVE, SUSPENDED_CLS)}
            log.info("tender_match: снапшот %s за %s, членов %d", source, d, len(out[source]))
        return out

    # ------------------------------------------------------- классификация
    def classify(self, okpd: Optional[str], subject: Optional[str], amount: Optional[float]) -> Optional[str]:
        okpd = (okpd or "").strip()
        subj = (subject or "").lower()
        design = tuple(str(p) for p in self.tcfg.get("design_okpd_prefixes", ["71"]))
        build = tuple(str(p) for p in self.tcfg.get("build_okpd_prefixes", ["41", "42", "43"]))
        if okpd.startswith(design):
            return TENDER_NO_SRO_DESIGN
        is_build = okpd.startswith(build) if okpd else any(k in subj for k in self.tcfg.get("build_keywords", []))
        if not is_build or amount is None:
            return None
        if amount > float(self.tcfg.get("build_high_threshold", 10_000_000)):
            return TENDER_NO_SRO_BUILD_HIGH
        if amount >= float(self.tcfg.get("build_mid_threshold", 5_000_000)):
            return TENDER_NO_SRO_BUILD_MID
        return None

    # -------------------------------------------------------------- файлы
    def process_file(self, path: Path, members: dict[str, Optional[set[str]]]) -> list[Signal]:
        spec = self.tcfg.get("columns", {})
        roles = self.tcfg.get("lead_roles", ["supplier"])
        require_snapshot = bool(self.tcfg.get("require_registry_snapshot", True))
        file_date = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
        signals: dict[tuple[str, str, str], Signal] = {}
        stats = {"rows": 0, "no_inn": 0, "in_registry": 0, "no_class": 0, "no_snapshot": 0}
        warned_sources: set[str] = set()

        sheets = pd.read_excel(path, sheet_name=None, header=None, dtype=object)
        for sheet_name, df in sheets.items():
            if df.empty:
                continue
            hdr = find_header_row(df, spec)
            if hdr is None:
                log.warning("tender_match: %s [%s]: не нашёл заголовок с ИНН, лист пропущен", path.name, sheet_name)
                continue
            cols = detect_columns(list(df.iloc[hdr]), spec)
            body = df.iloc[hdr + 1 :]

            def cell(row: Any, logical: str) -> Any:
                idx = cols.get(logical)
                if idx is None:
                    return None
                v = row.iloc[idx]
                return None if (isinstance(v, float) and v != v) else v

            for _, row in body.iterrows():
                stats["rows"] += 1
                amount = parse_money(cell(row, "sum"))
                okpd = clean_str(cell(row, "okpd"))
                subject = clean_str(cell(row, "subject"))
                sig_date = parse_date(cell(row, "date")) or file_date
                url = clean_str(cell(row, "url"))
                number = clean_str(cell(row, "number"))
                sig_type = self.classify(okpd, subject, amount)
                if sig_type is None:
                    stats["no_class"] += 1
                    continue
                need = ROLE_SOURCE[sig_type]
                for role in roles:
                    inn = normalize_inn(cell(row, f"{role}_inn"))
                    if not inn:
                        stats["no_inn"] += 1
                        continue
                    reg = members.get(need)
                    if reg is None:
                        if require_snapshot:
                            stats["no_snapshot"] += 1
                            if need not in warned_sources:
                                warned_sources.add(need)
                                log.warning("tender_match: нет снапшота %s — сигналы «%s» не создаём, "
                                            "сначала соберите реестр", need, sig_type)
                            continue
                    elif inn in reg:
                        stats["in_registry"] += 1
                        continue
                    key = (inn, sig_type, sig_date)
                    if key in signals:
                        continue
                    signals[key] = Signal(
                        inn=inn,
                        signal_type=sig_type,
                        signal_date=sig_date,
                        source="tenderguru",
                        url=url,
                        raw={
                            "name": clean_str(cell(row, f"{role}_name")),
                            "role": role,
                            "customer": clean_str(cell(row, "customer_name")),
                            "customer_inn": normalize_inn(cell(row, "customer_inn")),
                            "sum": amount,
                            "okpd": okpd,
                            "subject": subject,
                            "number": number,
                            "file": path.name,
                            "sheet": str(sheet_name),
                        },
                    )
        log.info("tender_match: %s: строк %d, сигналов %d, без ИНН %d, в реестре %d, не по теме %d, без снапшота %d",
                 path.name, stats["rows"], len(signals), stats["no_inn"], stats["in_registry"],
                 stats["no_class"], stats["no_snapshot"])
        return list(signals.values())

    def collect(self) -> list[Signal]:
        in_dir = resolve_path(self.config, "tenderguru_dir", "data/tenderguru")
        files = sorted(p for p in in_dir.glob(self.tcfg.get("file_glob", "*.xlsx"))
                       if p.is_file() and not p.name.startswith("~$"))
        if not files:
            log.info("tender_match: в %s нет новых выгрузок", in_dir)
            return []
        members = self.registry_members()
        signals: list[Signal] = []
        for path in files:
            try:
                signals.extend(self.process_file(path, members))
                self._done_files.append(path)
            except Exception:
                log.exception("tender_match: ошибка в файле %s, файл оставлен на месте", path.name)
        return signals

    def finalize(self) -> None:
        processed = resolve_path(self.config, "tenderguru_processed_dir", "data/tenderguru/processed")
        for path in self._done_files:
            target = processed / path.name
            if target.exists():
                target = processed / f"{path.stem}_{today_str()}{path.suffix}"
            shutil.move(str(path), str(target))
            log.info("tender_match: %s -> %s", path.name, target)
        self._done_files.clear()
