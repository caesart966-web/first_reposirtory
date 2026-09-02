"""Базовый класс коллектора и общая логика коллекторов реестров СРО."""
from __future__ import annotations

import gzip
import json
import logging
import time
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional

from core.db import Database
from core.models import (
    EXCLUDED_FROM_SRO,
    JOINED_SRO,
    SUSPENDED,
    RegistryRow,
    Signal,
    Snapshot,
)
from core.utils import HttpClient, clean_str, dig, normalize_inn, parse_date, resolve_path, today_str

log = logging.getLogger("sro_leads")


class CollectorError(Exception):
    """Ошибка коллектора: пишется в лог, остальные коллекторы продолжают работу."""


class Collector:
    """Коллектор возвращает список Signal и сам в БД не пишет.

    БД передаётся только для чтения (предыдущие снапшоты, сверка с реестром).
    Если коллектор собрал снапшот реестра, он кладёт его в `self.snapshot`,
    а записывает оркестратор — вместе с сигналами, одной транзакцией.
    """

    name: str = ""

    def __init__(self, config: dict[str, Any], db: Database, http: Optional[HttpClient] = None):
        self.config = config
        self.db = db
        self.http = http or HttpClient(config.get("http", {}))
        self.snapshot: Optional[Snapshot] = None
        self.backfill_days: Optional[int] = None  # --backfill N: задаёт оркестратор

    def collect(self) -> list[Signal]:
        raise NotImplementedError

    def finalize(self) -> None:
        """Вызывается оркестратором после успешной записи сигналов в БД
        (например, чтобы переложить обработанные файлы)."""


# ----------------------------------------------------------------------------
# Реестры НОСТРОЙ / НОПРИЗ: снапшот -> дифф со вчерашним -> сигналы
# ----------------------------------------------------------------------------
ACTIVE, SUSPENDED_CLS, EXCLUDED_CLS, UNKNOWN = "active", "suspended", "excluded", "unknown"
_RANK = {ACTIVE: 3, SUSPENDED_CLS: 2, UNKNOWN: 1, EXCLUDED_CLS: 0}


def classify_status(status: Optional[str], classes: dict[str, list[str]]) -> str:
    """Статус членства -> active | suspended | excluded | unknown (по подстрокам из конфига)."""
    s = (status or "").lower()
    if not s:
        return UNKNOWN
    for cls_name, key in ((EXCLUDED_CLS, "excluded"), (SUSPENDED_CLS, "suspended"), (ACTIVE, "active")):
        if any(sub.lower() in s for sub in classes.get(key, [])):
            return cls_name
    return UNKNOWN


def org_states(rows: list[RegistryRow], classes: dict[str, list[str]]) -> dict[str, tuple[str, RegistryRow]]:
    """Состояние организации по источнику: лучший статус среди всех её записей.

    Компания может числиться в нескольких СРО (или переехать из одной в другую):
    исключена из А, но действует в Б — это не лид.
    """
    best: dict[str, tuple[str, RegistryRow]] = {}
    for r in rows:
        cls = classify_status(r.status, classes)
        cur = best.get(r.inn)
        if cur is None or _RANK[cls] > _RANK[cur[0]] or (
            _RANK[cls] == _RANK[cur[0]] and (r.status_date or "") > (cur[1].status_date or "")
        ):
            best[r.inn] = (cls, r)
    return best


def diff_snapshots(
    prev_rows: list[RegistryRow],
    new_rows: list[RegistryRow],
    classes: dict[str, list[str]],
    source: str,
    snapshot_date: str,
) -> list[Signal]:
    """Сигналы по разнице двух снапшотов одного источника.

    signal_date — дата события из записи реестра (status_date для исключения/приостановки,
    reg_date для вступления); если в записи даты нет — дата снапшота, в котором событие
    обнаружено. Поэтому один и тот же лид из backfill и из диффа склеивается по UNIQUE.
    """
    prev = org_states(prev_rows, classes)
    new = org_states(new_rows, classes)
    signals: list[Signal] = []

    def make(inn: str, sig_type: str, row: RegistryRow, prev_cls: Optional[str], new_cls: Optional[str]) -> Signal:
        ev = row.reg_date if sig_type == JOINED_SRO else row.status_date
        return Signal(inn, sig_type, ev or snapshot_date, source, row.url, {
            "name": row.name, "sro_name": row.sro_name, "reg_number": row.reg_number,
            "status": row.status, "status_code": row.status_code, "event_date": ev,
            "prev_state": prev_cls, "new_state": new_cls, "snapshot_date": snapshot_date, "mode": "diff",
        }, detected_by="diff")

    for inn, (p_cls, p_row) in prev.items():
        if p_cls == EXCLUDED_CLS:
            continue  # уже был исключён — ничего нового
        n = new.get(inn)
        if n is None:
            signals.append(make(inn, EXCLUDED_FROM_SRO, p_row, p_cls, None))
            continue
        n_cls, n_row = n
        if n_cls == EXCLUDED_CLS:
            signals.append(make(inn, EXCLUDED_FROM_SRO, n_row, p_cls, n_cls))
        elif n_cls == SUSPENDED_CLS and p_cls != SUSPENDED_CLS:
            signals.append(make(inn, SUSPENDED, n_row, p_cls, n_cls))

    for inn, (n_cls, n_row) in new.items():
        if inn in prev:
            p_cls = prev[inn][0]
            # Восстановился после приостановки/исключения — считаем, что вступил (лид закрыт)
            if p_cls in (SUSPENDED_CLS, EXCLUDED_CLS) and n_cls == ACTIVE:
                signals.append(make(inn, JOINED_SRO, n_row, p_cls, n_cls))
            continue
        if n_cls in (ACTIVE, UNKNOWN):
            signals.append(make(inn, JOINED_SRO, n_row, None, n_cls))
        elif n_cls == SUSPENDED_CLS:
            signals.append(make(inn, SUSPENDED, n_row, None, n_cls))
        elif n_cls == EXCLUDED_CLS:
            signals.append(make(inn, EXCLUDED_FROM_SRO, n_row, None, n_cls))
    return signals


class RegistryCollector(Collector):
    """Общая логика для nostroy_registry и nopriz_registry. Различия — в config.yaml."""

    name = ""
    source = ""  # ключ в config.registry: nostroy | nopriz

    # ------------------------------------------------------------ настройки
    @property
    def rcfg(self) -> dict[str, Any]:
        return self.config.get("registry", {})

    @property
    def scfg(self) -> dict[str, Any]:
        cfg = self.rcfg.get(self.source)
        if not cfg:
            raise CollectorError(f"В config.yaml нет блока registry.{self.source}")
        return cfg

    # --------------------------------------------------------------- запрос
    def _page_body(self, page: int, page_size: Optional[int] = None) -> dict[str, Any]:
        body = json.loads(json.dumps(self.scfg.get("request_body") or {}))
        size = int(page_size or self.scfg.get("page_size", 500))
        body["page"] = page
        body["pageCount"] = str(size) if self.scfg.get("page_count_as_string", True) else size
        return body

    def _http_call(self, endpoint: str, page: int, page_size: Optional[int] = None) -> Any:
        url = self.scfg["base_url"].rstrip("/") + endpoint
        method = (self.scfg.get("method") or "POST").upper()
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if method == "GET":
            return self.http.get(url, params=self._page_body(page, page_size), headers=headers)
        return self.http.post(url, json=self._page_body(page, page_size), headers=headers)

    def _request(self, endpoint: str, page: int) -> Any:
        url = self.scfg["base_url"].rstrip("/") + endpoint
        resp = self._http_call(endpoint, page)
        if resp.status_code != 200:
            raise CollectorError(f"{self.source}: HTTP {resp.status_code} {url}")
        try:
            return resp.json()
        except ValueError as e:
            raise CollectorError(f"{self.source}: не JSON в ответе {url}: {e}") from e

    # ------------------------------------------------------------ check-api
    def check_api(self, page_size: int = 3) -> tuple[bool, str]:
        """Один запрос минимальной страницей и отчёт: статус, ключи, первые записи,
        сверка registry.<source>.fields с реальным ответом. В БД ничего не пишет.
        Возвращает (карта полей сошлась?, текст отчёта)."""
        fields = self.scfg.get("fields", {})
        lines: list[str] = []
        ok = True

        def probe(endpoint: str, title: str) -> Optional[Any]:
            nonlocal ok
            url = self.scfg["base_url"].rstrip("/") + endpoint
            lines.append(f"== {title}: {(self.scfg.get('method') or 'POST').upper()} {url}")
            lines.append(f"   тело запроса: {json.dumps(self._page_body(1, page_size), ensure_ascii=False)}")
            started = time.monotonic()
            try:
                resp = self._http_call(endpoint, 1, page_size)
            except Exception as e:
                ok = False
                lines.append(f"   ОШИБКА сети: {type(e).__name__}: {e}")
                return None
            elapsed = (time.monotonic() - started) * 1000
            lines.append(f"   HTTP {resp.status_code}, {elapsed:.0f} мс, {len(resp.content)} байт")
            if resp.status_code != 200:
                ok = False
                lines.append(f"   тело ответа: {resp.text[:500]!r}")
                return None
            try:
                data = resp.json()
            except ValueError:
                ok = False
                lines.append(f"   ответ не JSON: {resp.text[:500]!r}")
                return None
            lines.append(f"   ключи верхнего уровня: {list(data.keys()) if isinstance(data, dict) else type(data).__name__}")
            return data

        def which(obj: Any, paths: Any) -> tuple[Optional[str], Any]:
            for path in ([paths] if isinstance(paths, str) else list(paths or [])):
                v = dig(obj, path)
                if v is not None:
                    return path, v
            return None, None

        def short(v: Any) -> str:
            t = json.dumps(v, ensure_ascii=False, default=str)
            return t if len(t) <= 80 else t[:77] + "..."

        sro_list_ep = self.scfg.get("sro_list_endpoint")
        members_ep = self.scfg["members_endpoint"]
        if sro_list_ep:
            data = probe(sro_list_ep, "список СРО")
            sros = dig(data, fields.get("items"), default=[]) if data else []
            if not isinstance(sros, list) or not sros:
                ok = False
                lines.append("   список СРО пуст или не найден по fields.items — проверьте registry.fields")
                return ok, "\n".join(lines)
            sro_id = dig(sros[0], ["id", "sro_id"])
            lines.append(f"   первая СРО: id={sro_id}, {short(sros[0])}")
            members_ep = members_ep.replace("{sro_id}", str(sro_id))

        data = probe(members_ep, "реестр членов")
        if data is None:
            return False, "\n".join(lines)

        items_path, items = which(data, fields.get("items"))
        total_path, total = which(data, fields.get("total"))
        lines.append("")
        lines.append("== Сверка registry.%s.fields с ответом (по первой записи):" % self.source)
        lines.append(f"   {'поле':<12} {'путь в ответе':<32} значение")
        lines.append(f"   {'items':<12} {items_path or 'НЕ НАЙДЕНО':<32} "
                     f"{'список из %d записей' % len(items) if isinstance(items, list) else 'не список: ' + short(items)}")
        lines.append(f"   {'total':<12} {total_path or 'НЕ НАЙДЕНО':<32} {short(total)}")
        if not isinstance(items, list) or not items:
            ok = False
            lines.append("   ЗАПИСЕЙ НЕТ: проверьте fields.items, тело запроса (pageCount строкой?) и эндпоинт")
            return ok, "\n".join(lines)

        first = items[0]
        lines.append("")
        lines.append(f"== Первые {min(3, len(items))} записи:")
        for i, it in enumerate(items[:3], 1):
            lines.append(f"--- запись {i}")
            lines.append(json.dumps(it, ensure_ascii=False, indent=2, default=str))
        lines.append("")
        lines.append("== Поля записи:")
        required = {"inn", "status"}
        for name, paths in fields.items():
            if name in ("items", "total"):
                continue
            path, value = which(first, paths)
            mark = ""
            if path is None:
                mark = "  <-- НЕ НАЙДЕНО" + (" (обязательное)" if name in required else "")
                if name in required:
                    ok = False
            lines.append(f"   {name:<12} {path or '-':<32} {short(value) if path else '-'}{mark}")
        if not fields.get("status_date"):
            lines.append("   status_date  не задано в config.yaml — backfill работать не будет")
        inn_norm = normalize_inn(dig(first, fields.get("inn")))
        lines.append("")
        lines.append(f"   ИНН первой записи после нормализации: {inn_norm or 'НЕ РАСПОЗНАН'}")
        lines.append(f"   статус первой записи -> класс: {classify_status(clean_str(dig(first, fields.get('status'))), self.rcfg.get('status_classes', {}))}")
        lines.append("")
        lines.append(f"== Итог: записей заявлено {total if total is not None else 'неизвестно (fields.total не найден)'}; "
                     f"карта полей {'сошлась' if ok else 'НЕ СОШЛАСЬ — правьте registry.%s в config.yaml' % self.source}")
        return ok, "\n".join(lines)

    def _fetch_pages(self, endpoint: str, label: str) -> list[dict[str, Any]]:
        fields = self.scfg.get("fields", {})
        items: list[dict[str, Any]] = []
        total: Optional[int] = None
        max_pages = int(self.rcfg.get("max_pages", 5000))
        delay = float(self.rcfg.get("page_delay", 0))
        for page in range(1, max_pages + 1):
            data = self._request(endpoint, page)
            chunk = dig(data, fields.get("items"), default=[])
            if not isinstance(chunk, list):
                raise CollectorError(f"{self.source}: поле items не список (страница {page})")
            if total is None:
                t = dig(data, fields.get("total"))
                total = int(t) if isinstance(t, (int, float, str)) and str(t).isdigit() else None
            if not chunk:
                break
            items.extend(chunk)
            log.info("%s %s: страница %d, записей %d%s", self.source, label, page, len(items),
                     f" из {total}" if total else "")
            if total is not None and len(items) >= total:
                break
            if delay:
                time.sleep(delay)
        return items

    def fetch_all(self) -> list[dict[str, Any]]:
        """Полная выгрузка реестра: одним эндпоинтом или обходом по СРО."""
        sro_list_ep = self.scfg.get("sro_list_endpoint")
        members_ep = self.scfg["members_endpoint"]
        if not sro_list_ep:
            return self._fetch_pages(members_ep, "реестр")
        sros = self._fetch_pages(sro_list_ep, "список СРО")
        all_items: list[dict[str, Any]] = []
        for i, sro in enumerate(sros, 1):
            sro_id = dig(sro, ["id", "sro_id"])
            if sro_id is None:
                continue
            log.info("%s: СРО %d/%d (id=%s)", self.source, i, len(sros), sro_id)
            for item in self._fetch_pages(members_ep.replace("{sro_id}", str(sro_id)), f"СРО {sro_id}"):
                item.setdefault("sro", {})
                if isinstance(item["sro"], dict):
                    item["sro"].setdefault("id", sro_id)
                    for k in ("short_description", "full_description", "name"):
                        if k in sro and k not in item["sro"]:
                            item["sro"][k] = sro[k]
                all_items.append(item)
        return all_items

    # ----------------------------------------------------------- маппинг
    def to_rows(self, items: list[dict[str, Any]]) -> list[RegistryRow]:
        fields = self.scfg.get("fields", {})
        url_tpl = self.scfg.get("member_url") or ""
        rows: list[RegistryRow] = []
        bad = 0
        for it in items:
            inn = normalize_inn(dig(it, fields.get("inn")))
            if not inn:
                bad += 1
                continue
            sro_name = clean_str(dig(it, fields.get("sro_name"))) or "?"
            url = None
            if url_tpl:
                try:
                    url = url_tpl.format(
                        sro_id=dig(it, fields.get("sro_id"), ""),
                        member_id=dig(it, fields.get("member_id"), ""),
                        inn=inn,
                    )
                except (KeyError, IndexError):
                    url = None
            rows.append(
                RegistryRow(
                    inn=inn,
                    sro_name=sro_name,
                    reg_number=clean_str(dig(it, fields.get("reg_number"))),
                    status=clean_str(dig(it, fields.get("status"))),
                    name=clean_str(dig(it, fields.get("name"))),
                    url=url,
                    status_code=clean_str(dig(it, fields.get("status_code"))),
                    status_date=parse_date(dig(it, fields.get("status_date"))),
                    reg_date=parse_date(dig(it, fields.get("reg_date"))),
                )
            )
        if bad:
            log.warning("%s: записей без корректного ИНН: %d", self.source, bad)
        return rows

    # ---------------------------------------------------------------- диск
    def save_raw(self, items: list[dict[str, Any]], snapshot_date: str, failed: bool = False) -> Path:
        snap_dir = resolve_path(self.config, "snapshots_dir", "data/snapshots")
        suffix = ".failed" if failed else ""
        payload = json.dumps(items, ensure_ascii=False).encode("utf-8")
        if self.rcfg.get("compress_raw", True):
            path = snap_dir / f"{self.source}_{snapshot_date}{suffix}.json.gz"
            with gzip.open(path, "wb") as f:
                f.write(payload)
        else:
            path = snap_dir / f"{self.source}_{snapshot_date}{suffix}.json"
            path.write_bytes(payload)
        return path

    # -------------------------------------------------------------- collect
    # ------------------------------------------------------------- backfill
    def backfill_signals(self, rows: list[RegistryRow], today: str) -> list[Signal]:
        """Сигналы из самих записей: прекращённые/приостановленные с датой события в окне N дней."""
        days = int(self.backfill_days or 0)
        field = self.scfg.get("fields", {}).get("status_date")
        if not field:
            raise CollectorError(
                f"{self.source}: backfill невозможен, в config.yaml нет registry.{self.source}.fields.status_date")
        if not any(r.status_date for r in rows):
            raise CollectorError(
                f"{self.source}: backfill невозможен, в ответе нет поля {field} (пусто у всех записей), "
                f"проверьте registry.{self.source}.fields в config.yaml")
        window_start = (date.fromisoformat(today) - timedelta(days=days)).isoformat()
        classes = self.rcfg.get("status_classes", {})
        signals: list[Signal] = []
        stats = {"in_window": 0, "older": 0, "no_date": 0}
        for inn, (cls, row) in org_states(rows, classes).items():
            if cls not in (EXCLUDED_CLS, SUSPENDED_CLS):
                continue
            if not row.status_date:
                stats["no_date"] += 1
                continue
            if row.status_date < window_start or row.status_date > today:
                stats["older"] += 1
                continue
            stats["in_window"] += 1
            sig_type = EXCLUDED_FROM_SRO if cls == EXCLUDED_CLS else SUSPENDED
            signals.append(Signal(inn, sig_type, row.status_date, self.source, row.url, {
                "name": row.name, "sro_name": row.sro_name, "reg_number": row.reg_number,
                "status": row.status, "status_code": row.status_code, "event_date": row.status_date,
                "prev_state": None, "new_state": cls, "snapshot_date": today, "mode": "backfill",
            }, detected_by="backfill"))
        log.info("%s: backfill за %d дней (с %s): сигналов %d, старше окна %d, без даты %d",
                 self.source, days, window_start, stats["in_window"], stats["older"], stats["no_date"])
        return signals

    # -------------------------------------------------------------- collect
    def collect(self) -> list[Signal]:
        today = today_str()
        if self.db.has_snapshot(self.source, today):
            if self.backfill_days:
                log.info("%s: снапшот за %s уже есть — backfill по нему из БД, реестр не перекачиваем",
                         self.source, today)
                return self.backfill_signals(self.db.snapshot_rows(self.source, today), today)
            log.info("%s: снапшот за %s уже есть, повторно не собираем (ложных диффов не будет)",
                     self.source, today)
            return []

        items = self.fetch_all()
        rows = self.to_rows(items)
        log.info("%s: получено записей %d, валидных %d", self.source, len(items), len(rows))

        prev_date = self.db.latest_snapshot_date(self.source, before=today)
        prev_rows = self.db.snapshot_rows(self.source, prev_date) if prev_date else []

        ratio = float(self.rcfg.get("min_size_ratio", 0.5))
        if not rows or (prev_rows and len(rows) < ratio * len(prev_rows)):
            path = self.save_raw(items, today, failed=True)
            raise CollectorError(
                f"{self.source}: снапшот подозрительно мал ({len(rows)} строк против {len(prev_rows)} "
                f"в предыдущем, порог {ratio:.0%}) — считаем сбоем API, дифф не строим. Сырой ответ: {path}"
            )

        path = self.save_raw(items, today)
        log.info("%s: сырой снапшот сохранён: %s", self.source, path)
        self.snapshot = Snapshot(self.source, today, rows)

        if self.backfill_days:
            return self.backfill_signals(rows, today)

        if not prev_rows:
            log.info("%s: предыдущего снапшота нет — первый день, сигналов не будет", self.source)
            return []

        classes = self.rcfg.get("status_classes", {})
        signals = diff_snapshots(prev_rows, rows, classes, self.source, today)
        counts: dict[str, int] = defaultdict(int)
        for s in signals:
            counts[s.signal_type] += 1
        log.info("%s: дифф с %s: %s", self.source, prev_date, dict(counts) or "изменений нет")
        return signals
