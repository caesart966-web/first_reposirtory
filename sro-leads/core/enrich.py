"""Обогащение организаций: Dadata по ИНН -> локальные справочники -> сайт (поиск + парсинг контактов).

Только для организаций со скором >= enrich.min_score, не чаще раза в enrich.reenrich_after_days.
Ликвидированные помечаются в orgs.status, экспорт их не берёт.
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse

import pandas as pd
from bs4 import BeautifulSoup

from .db import Database
from .models import Org
from .utils import HttpClient, clean_str, days_ago, domain_of, normalize_inn, now_str, resolve_path

log = logging.getLogger("sro_leads")

LIQUIDATED_STATUSES = {"LIQUIDATED", "LIQUIDATING", "BANKRUPT"}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+7|8)[\s\-(]*(\d{3})[\s\-)]*(\d{3})[\s\-]*(\d{2})[\s\-]*(\d{2})")
BAD_EMAIL_PARTS = ("example.", "sentry", "wixpress", ".png", ".jpg", ".gif", ".svg", "@2x", "noreply", "no-reply")

LOCAL_COLUMNS = {
    "inn": ["инн"],
    "name": ["название", "наименование"],
    "ogrn": ["огрн"],
    "address": ["адрес"],
    "phone": ["телефон"],
    "email": ["email", "e-mail", "почта"],
    "site": ["сайт", "site"],
    "okved": ["оквэд", "вид деятельности"],
    "director": ["руководитель"],
    "director_last": ["фамилия руководителя"],
    "director_first": ["имя руководителя"],
    "director_middle": ["отчество руководителя"],
}


def format_phone(m: re.Match) -> str:
    return f"+7 ({m.group(1)}) {m.group(2)}-{m.group(3)}-{m.group(4)}"


def extract_contacts(html: str) -> tuple[list[str], list[str]]:
    """Почты и телефоны со страницы: mailto:/tel: и регулярки по тексту."""
    emails: list[str] = []
    phones: list[str] = []
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().startswith("mailto:"):
            emails.append(href[7:].split("?")[0].strip())
        elif href.lower().startswith("tel:"):
            m = PHONE_RE.search(href[4:])
            if m:
                phones.append(format_phone(m))
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(" ")
    emails += EMAIL_RE.findall(text)
    phones += [format_phone(m) for m in PHONE_RE.finditer(text)]

    def uniq(items: list[str], limit: int = 3) -> list[str]:
        out: list[str] = []
        for x in items:
            x = x.strip().lower() if "@" in x else x.strip()
            if x and x not in out:
                out.append(x)
            if len(out) >= limit:
                break
        return out

    emails = [e for e in uniq(emails, 10) if not any(b in e for b in BAD_EMAIL_PARTS)][:3]
    return emails, uniq(phones)


def name_core(name: Optional[str]) -> Optional[str]:
    """Самое длинное слово названия без ОПФ — для проверки, что сайт действительно этой компании."""
    if not name:
        return None
    words = re.findall(r"[А-Яа-яЁёA-Za-z0-9\-]{4,}", name)
    stop = {"ооо", "оао", "зао", "пао", "акционерное", "общество", "ограниченной", "ответственностью",
            "компания", "группа", "строй", "строительная", "строительство", "фирма", "холдинг"}
    words = [w for w in words if w.lower() not in stop]
    return max(words, key=len).lower() if words else None


class Enricher:
    def __init__(self, config: dict[str, Any], db: Database, http: Optional[HttpClient] = None):
        self.config = config
        self.db = db
        self.http = http or HttpClient(config.get("http", {}))
        self.ecfg = config.get("enrich", {})
        self.dadata_token = os.environ.get("DADATA_TOKEN", "").strip()
        self._local: Optional[dict[str, dict[str, Any]]] = None
        self._warned_no_token = False

    # ---------------------------------------------------------------- Dadata
    def dadata_lookup(self, inn: str) -> Optional[dict[str, Any]]:
        dcfg = self.ecfg.get("dadata", {})
        if not dcfg.get("enabled", True):
            return None
        if not self.dadata_token:
            if not self._warned_no_token:
                log.warning("Dadata: DADATA_TOKEN не задан в .env — обогащение по ИНН через Dadata пропущено")
                self._warned_no_token = True
            return None
        resp = self.http.post(
            dcfg.get("url", "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"),
            json={"query": inn, "count": 1},
            headers={"Authorization": f"Token {self.dadata_token}", "Accept": "application/json",
                     "Content-Type": "application/json"},
        )
        if resp.status_code != 200:
            log.warning("Dadata: HTTP %s для ИНН %s", resp.status_code, inn)
            return None
        suggestions = (resp.json() or {}).get("suggestions") or []
        return suggestions[0] if suggestions else None

    @staticmethod
    def parse_dadata(inn: str, sug: dict[str, Any]) -> Org:
        d = sug.get("data") or {}
        name = (d.get("name") or {})
        address = d.get("address") or {}
        adata = address.get("data") or {}
        director = None
        if d.get("type") == "INDIVIDUAL":
            fio = d.get("fio") or {}
            director = " ".join(x for x in (fio.get("surname"), fio.get("name"), fio.get("patronymic")) if x) or None
        else:
            director = (d.get("management") or {}).get("name")
        emails = [e.get("value") if isinstance(e, dict) else str(e) for e in (d.get("emails") or [])]
        phones = [p.get("value") if isinstance(p, dict) else str(p) for p in (d.get("phones") or [])]
        region = adata.get("region_with_type") or None
        if not region and address.get("value"):
            region = address["value"].split(",")[0].strip() or None
        return Org(
            inn=inn,
            ogrn=clean_str(d.get("ogrn")),
            name=clean_str(name.get("short_with_opf") or name.get("full_with_opf") or sug.get("value")),
            region=clean_str(region),
            address=clean_str(address.get("unrestricted_value") or address.get("value")),
            okved=clean_str(d.get("okved")),
            director=clean_str(director),
            status=clean_str((d.get("state") or {}).get("status")),
            email=", ".join(e for e in emails if e) or None,
            phone=", ".join(p for p in phones if p) or None,
        )

    # --------------------------------------------------- локальный справочник
    def local_directory(self) -> dict[str, dict[str, Any]]:
        if self._local is not None:
            return self._local
        self._local = {}
        lcfg = self.ecfg.get("local_directory", {})
        if not lcfg.get("enabled", True):
            return self._local
        cdir = resolve_path(self.config, "companies_dir", "data/companies")
        for path in sorted(cdir.glob(lcfg.get("file_glob", "*.xlsx"))):
            if path.name.startswith("~$"):
                continue
            try:
                self._local.update(self.load_directory_file(path))
                log.info("Локальный справочник %s: всего записей %d", path.name, len(self._local))
            except Exception:
                log.exception("Локальный справочник %s: не прочитан", path.name)
        return self._local

    @staticmethod
    def load_directory_file(path: Path) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for _, df in pd.read_excel(path, sheet_name=None, dtype=object).items():
            headers = [str(h).strip().lower() for h in df.columns]
            cols: dict[str, int] = {}
            for logical, keys in LOCAL_COLUMNS.items():
                for idx, h in enumerate(headers):
                    if idx in cols.values():
                        continue
                    if any(k in h for k in keys):
                        # "руководитель" не должен перехватить "фамилия руководителя"
                        if logical == "director" and "руководителя" in h:
                            continue
                        cols[logical] = idx
                        break
            if "inn" not in cols:
                continue
            for row in df.itertuples(index=False):
                inn = normalize_inn(row[cols["inn"]])
                if not inn:
                    continue
                rec: dict[str, Any] = {}
                for logical, idx in cols.items():
                    v = row[idx]
                    if v is None or (isinstance(v, float) and v != v):
                        continue
                    rec[logical] = clean_str(v)
                fio = [rec.pop(k, None) for k in ("director_last", "director_first", "director_middle")]
                if any(fio) and not rec.get("director"):
                    rec["director"] = " ".join(x for x in fio if x)
                rec.pop("inn", None)
                out[inn] = {k: v for k, v in rec.items() if v}
        return out

    # ------------------------------------------------------------------ сайт
    def find_site(self, name: Optional[str], inn: str) -> Optional[str]:
        scfg = self.ecfg.get("site_search", {})
        if not scfg.get("enabled", True) or not scfg.get("url"):
            return None
        query = f"{name or ''} {inn}".strip()
        try:
            resp = self.http.get(scfg["url"].format(query=quote_plus(query)))
        except Exception as e:  # сеть — не повод падать
            log.warning("Поиск сайта для %s: %s", inn, e)
            return None
        if resp.status_code != 200:
            return None
        skip = {d.lower() for d in scfg.get("skip_domains", [])}
        soup = BeautifulSoup(resp.text, "lxml")
        for a in soup.select("a.result__a, a.result__url, h2 a, a[href]"):
            href = a.get("href") or ""
            if "uddg=" in href:
                href = unquote(parse_qs(urlparse(href).query).get("uddg", [""])[0])
            if not href.startswith("http"):
                continue
            dom = domain_of(href)
            if not dom or any(dom == s or dom.endswith("." + s) for s in skip):
                continue
            return f"{urlparse(href).scheme}://{urlparse(href).netloc}/"
        return None

    def parse_site(self, site: str, inn: str, name: Optional[str]) -> tuple[Optional[str], Optional[str], bool]:
        """(email, phone, confirmed): confirmed = на сайте нашлись ИНН или ядро названия."""
        pcfg = self.ecfg.get("site_parse", {})
        if not pcfg.get("enabled", True):
            return None, None, False
        base = site if site.startswith("http") else "http://" + site
        emails: list[str] = []
        phones: list[str] = []
        confirmed = False
        core = name_core(name)
        for page in pcfg.get("pages", ["/", "/contacts", "/kontakty", "/about"]):
            url = urljoin(base, page)
            try:
                resp = self.http.get(url, allow_redirects=True, stream=True)
                if resp.status_code != 200 or "html" not in resp.headers.get("Content-Type", "").lower():
                    continue
                html = resp.raw.read(int(pcfg.get("max_bytes", 2_000_000)), decode_content=True).decode(
                    resp.encoding or "utf-8", errors="replace")
            except Exception as e:
                log.debug("Сайт %s: %s", url, e)
                continue
            low = html.lower()
            if inn in html or (core and core in low):
                confirmed = True
            e, p = extract_contacts(html)
            emails += [x for x in e if x not in emails]
            phones += [x for x in p if x not in phones]
        return (", ".join(emails[:3]) or None, ", ".join(phones[:3]) or None, confirmed)

    # ------------------------------------------------------------- пайплайн
    def candidates(self, limit: int) -> list[str]:
        min_score = float(self.ecfg.get("min_score", 60))
        cutoff = days_ago(int(self.ecfg.get("reenrich_after_days", 30)))
        rows = self.db.conn.execute(
            "SELECT inn FROM orgs WHERE score >= ? AND (enriched_at IS NULL OR enriched_at < ?) "
            "ORDER BY score DESC LIMIT ?",
            (min_score, cutoff, limit),
        ).fetchall()
        return [r["inn"] for r in rows]

    def enrich_one(self, inn: str) -> Org:
        current = self.db.get_org(inn) or Org(inn=inn)
        org = Org(inn=inn)

        sug = self.dadata_lookup(inn)
        if sug:
            org = self.parse_dadata(inn, sug)

        local = self.local_directory().get(inn)
        if local:
            for k in ("name", "ogrn", "address", "okved", "director", "phone", "email", "site"):
                if not getattr(org, k) and local.get(k):
                    setattr(org, k, local[k])

        if org.status in LIQUIDATED_STATUSES:
            org.enriched_at = now_str()
            log.info("%s %s: %s, в экспорт не пойдёт", inn, org.name or "", org.status)
            return org

        name = org.name or current.name
        site = org.site or current.site
        if not site:
            site = self.find_site(name, inn)
        if site and (not org.phone or not org.email):
            email, phone, confirmed = self.parse_site(site, inn, name)
            if confirmed or org.site or current.site:
                org.site = site
                org.email = org.email or email
                org.phone = org.phone or phone
            else:
                log.info("%s: сайт %s не подтверждён (нет ИНН/названия на страницах), отброшен", inn, site)
        elif site:
            org.site = site
        org.enriched_at = now_str()
        return org

    def run(self, limit: Optional[int] = None) -> dict[str, int]:
        limit = limit or int(self.ecfg.get("max_per_run", 200))
        inns = self.candidates(limit)
        stats = {"candidates": len(inns), "enriched": 0, "liquidated": 0, "errors": 0}
        log.info("Обогащение: кандидатов %d (скор >= %s)", len(inns), self.ecfg.get("min_score", 60))
        for i, inn in enumerate(inns, 1):
            try:
                org = self.enrich_one(inn)
                self.db.upsert_org(org)
                self.db.commit()
                stats["enriched"] += 1
                if org.status in LIQUIDATED_STATUSES:
                    stats["liquidated"] += 1
                log.info("Обогащено %d/%d: %s %s | сайт=%s тел=%s почта=%s", i, len(inns), inn,
                         org.name or "", org.site or "-", org.phone or "-", org.email or "-")
            except Exception:
                stats["errors"] += 1
                self.db.rollback()
                log.exception("Обогащение %s: ошибка", inn)
        return stats
